"""
Process to read Kafka messages and save a summary to the database
"""
import codecs
import datetime
import json
import logging
import re
import signal
import socket
import time
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

import pykafka
import pytz
from dhcpkit.common.server.logging.verbosity import set_verbosity_logger
from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.messages import RelayReplyMessage, ClientServerMessage
from dhcpkit.ipv6.options import ClientIdOption, InterfaceIdOption
from dhcpkit.ipv6.utils import split_relay_chain
from dhcpkit.protocol_element import JSONProtocolElementEncoder
from dhcpkit_kafka.messages import KafkaMessage, DHCPKafkaMessage
from django.core.management.base import BaseCommand
from pykafka.exceptions import ConsumerStoppedException
from typing import Dict

from dhcpkit_looking_glass import app_settings
from dhcpkit_looking_glass.models import Client, Server, Transaction

logger = logging.getLogger()


def _format_host_port(host: str, port: int) -> str:
    """
    Utility function to create a nice host+port string with proper IPv6 escaping.

    :param host: The hostname or IP address string
    :param port: The port number
    :return: The formatted host+port
    """
    if not host:
        # Default hostname
        host = socket.getfqdn()

    if ':' in host:
        host = '[{}]'.format(host)

    if port:
        return '{}:{}'.format(host, port)
    else:
        return host


def _fix_broker(broker: str) -> str:
    """
    Add a port number if necessary.

    :param broker: Raw broker name
    :return: Fixed broker name
    """
    if not re.match(':\d+$', broker):
        broker += ':9092'

    return broker


stopping = False


# noinspection PyUnusedLocal
def signal_stop(signum, frame):
    """
    Signal that we are stopping
    """
    logger.info("Stopping...")
    global stopping
    stopping = True


class Command(BaseCommand):
    """
    Process to read Kafka messages and save a summary to the database
    """
    help = 'Process Kafka messages for the looking glass'

    def add_arguments(self, parser: ArgumentParser):
        """
        Set up command line arguments

        :param parser: The command line parser
        """
        parser.add_argument('-b', '--brokers', nargs='+', metavar='HOST:PORT', default=['localhost:9092'],
                            help='The Kafka brokers to bootstrap from')
        parser.add_argument('-s', '--source-address',
                            help='Source address to use when connecting to Kafka')
        parser.add_argument('-t', '--topic', default='dhcpkit.messages',
                            help='The topic to subscribe to')
        parser.add_argument('-g', '--consumer-group', default='dhcpkit_looking_glass',
                            help='The consumer group we belong to, for progress tracking')
        parser.add_argument('--from-beginning', action='store_true',
                            help='Start processing messages from the beginning instead of continuing')

        parser.formatter_class = ArgumentDefaultsHelpFormatter

    def handle(self, *args, **options):
        """
        Handle Kafka messages

        :param args: Command line args, should be empty
        :param options: The command line options
        """
        # Set up some basic logging
        set_verbosity_logger(logger, options['verbosity'])

        signal.signal(signal.SIGINT, signal_stop)
        signal.signal(signal.SIGTERM, signal_stop)

        while not stopping:
            try:
                # noinspection PyTypeChecker
                kafka = pykafka.KafkaClient(hosts=','.join(map(_fix_broker, options['brokers'])),
                                            source_address=options['source_address'] or '')

                kafka_topic = kafka.topics[options['topic'].encode('ascii')]

                kafka_consumer = kafka_topic.get_balanced_consumer(
                    consumer_group=options['consumer_group'].encode('ascii'),
                    auto_commit_enable=True,
                    reset_offset_on_start=options['from_beginning'],
                    consumer_timeout_ms=1000
                )

                while not stopping:
                    for incoming_message in kafka_consumer:
                        try:
                            length, message = KafkaMessage.parse(incoming_message.value)
                            if not isinstance(message, DHCPKafkaMessage):
                                # We aren't interested in this message
                                continue

                            self.process_message(message)
                        except Exception as e:
                            logger.error("Received invalid message from Kafka: {}".format(e))

            except ConsumerStoppedException:
                return

            except Exception as e:
                logger.critical(str(e))
                time.sleep(5)
                logger.info("Restarting")

    @staticmethod
    def get_transaction_info(message: DHCPKafkaMessage) -> Dict[str, object]:
        """
        Extract interesting data from the incoming message

        :param message: The Kafka DHCP message
        :return: A dictionary of stuff
        """
        # Split the message into usable blocks
        request, incoming_relay_messages = split_relay_chain(message.message_in)

        # Get the DUID and create representations for in the database
        duid_obj = request.get_option_of_type(ClientIdOption).duid
        duid = '0x' + codecs.encode(duid_obj.save(), 'hex').decode('ascii')

        # Get the link-local address of the client
        link_local = str(incoming_relay_messages[0].peer_address)

        # Get the Interface ID and create representation for in the database
        interface_id_obj = incoming_relay_messages[0].get_option_of_type(InterfaceIdOption)
        if interface_id_obj:
            try:
                interface_id = interface_id_obj.interface_id.decode('ascii')
            except ValueError:
                interface_id = '0x' + codecs.encode(interface_id_obj.interface_id, 'hex').decode('ascii')
        else:
            interface_id = ''

        # Get the Remote ID and create representation for in the database
        remote_id_obj = incoming_relay_messages[0].get_option_of_type(RemoteIdOption)
        if remote_id_obj:
            try:
                remote_id = '{}:{}'.format(remote_id_obj.enterprise_number, remote_id_obj.remote_id.decode('ascii'))
            except ValueError:
                remote_id = '{}:0x{}'.format(remote_id_obj.enterprise_number,
                                             codecs.encode(remote_id_obj.remote_id, 'hex').decode('ascii'))
        else:
            remote_id = ''

        # Get the request type
        request_type = request.__class__.__name__
        if request_type.endswith('Message'):
            request_type = request_type[:-7]

        # Get the response type
        response = message.message_out
        while isinstance(response, RelayReplyMessage):
            response = response.relayed_message

        if isinstance(response, ClientServerMessage):
            response_type = response.__class__.__name__
        else:
            response_type = None

        return {
            'duid': duid,
            'interface_id': interface_id,
            'remote_id': remote_id,
            'link_local': link_local,
            'request_type': request_type,
            'response_type': response_type,
        }

    def process_message(self, message: DHCPKafkaMessage):
        """
        Process a single KafkaMessage

        :param message: The message
        """
        # Do we have an incoming message?
        if not message.message_in:
            return

        # Extract transaction info
        info = self.get_transaction_info(message)

        # Get the server and client
        server, created = Server.objects.get_or_create(name=message.server_name)
        if created:
            logger.info("Discovered new server: {}".format(server))

        client, created = Client.objects.get_or_create(duid=info['duid'],
                                                       interface_id=info['interface_id'],
                                                       remote_id=info['remote_id'])
        if created:
            logger.info("Discovered new client: {}".format(client))

        # Save the response
        logger.info("Saving DHCP transaction from {} to {}".format(client, server))

        request_ts = datetime.datetime.utcfromtimestamp(message.timestamp_in).replace(tzinfo=pytz.utc)
        request = (json.dumps(message.message_in, cls=JSONProtocolElementEncoder)
                   if message.message_in else '')

        response_ts = datetime.datetime.utcfromtimestamp(message.timestamp_out).replace(tzinfo=pytz.utc)
        response = (json.dumps(message.message_out, cls=JSONProtocolElementEncoder)
                    if message.message_out else '')

        Transaction.objects.update_or_create(client=client,
                                             server=server,
                                             request_ts=request_ts,
                                             defaults={
                                                 'request_type': info['request_type'],
                                                 'request': request,
                                                 'request_ll': info['link_local'],

                                                 'response_type': info['response_type'],
                                                 'response_ts': response_ts,
                                                 'response': response,
                                             })

        # Only keep the last transactions per client/server
        if app_settings.MAX_TRANSACTIONS or app_settings.MAX_TRANSACTION_AGE:
            my_transactions = Transaction.objects.filter(client=client, server=server)
            keep = my_transactions

            if app_settings.MAX_TRANSACTION_AGE:
                deadline = request_ts - app_settings.MAX_TRANSACTION_AGE
                keep = keep.filter(request_ts__gte=deadline)

            if app_settings.MAX_TRANSACTIONS:
                keep = keep.order_by('-request_ts')[:app_settings.MAX_TRANSACTIONS]

            delete = my_transactions.exclude(pk__in=keep)
            deleted, per_model = delete.delete()
            if deleted:
                logger.debug("Deleted {} old transactions".format(deleted))
