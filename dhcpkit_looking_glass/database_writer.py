"""
We put the database writer in a separate process so we don't slow down the main request handling
"""
import codecs
import json
import multiprocessing
import sqlite3

from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.options import InterfaceIdOption, ClientIdOption
from dhcpkit.ipv6.transaction_bundle import TransactionBundle
from dhcpkit.protocol_element import JSONProtocolElementEncoder
from dhcpkit.utils import camelcase_to_dash

# Our private multiprocessing context
ctx = multiprocessing.get_context('spawn')


class DatabaseProcess(ctx.Process):
    """
    Separate process for writing looking glass data to the database.
    """

    def __init__(self, filename, log_request_options, log_response_options):
        super().__init__()

        self.daemon = True
        self.queue = ctx.Queue(maxsize=1000)

        self.filename = filename

        self.log_request_options = []
        if log_request_options:
            for option in log_request_options:
                try:
                    option = int(option)
                except ValueError:
                    option = camelcase_to_dash(str(option))
                    if not option.endswith('-option'):
                        option += '-option'

                self.log_request_options.append(option)

        self.log_response_options = []
        if log_response_options:
            for option in log_response_options:
                try:
                    option = int(option)
                except ValueError:
                    option = camelcase_to_dash(str(option))
                    if not option.endswith('-option'):
                        option += '-option'

                self.log_response_options.append(option)

    @staticmethod
    def get_options_json(options: list, option_types: list):
        """
        Get the specified option types from the message. Option types can be specified as an integer or as a dash-style
        option class name (e.g. 'remote-id-option').

        :param options: The list of options in the message
        :param option_types: The list of option types to return
        :return: The requested options in JSON format
        """
        wanted_options = [option for option in options
                          if option.option_type in option_types or
                          camelcase_to_dash(option.__class__.__name__) in option_types]

        return json.dumps(wanted_options, cls=JSONProtocolElementEncoder)

    def run(self):
        """
        Implementation of the worker thread.
        """
        # Connect to the database from the process
        db = sqlite3.connect(self.filename, check_same_thread=False)

        # Create tables if necessary
        cur = db.cursor()
        cur.execute("PRAGMA JOURNAL_MODE=WAL")
        cur.execute("CREATE TABLE IF NOT EXISTS clients ("
                    "  duid TEXT NOT NULL, "
                    "  duid_ll TEXT NOT NULL, "
                    "  interface_id TEXT NOT NULL, "
                    "  remote_id TEXT NOT NULL, "

                    "  last_request_transaction TEXT, "
                    "  last_request_type TEXT, "
                    "  last_request_ts DATETIME, "
                    "  last_request_options TEXT, "

                    "  last_response_transaction TEXT, "
                    "  last_response_type TEXT, "
                    "  last_response_ts DATETIME, "
                    "  last_response_options TEXT, "

                    "  PRIMARY KEY(duid, interface_id, remote_id)"
                    ") WITHOUT ROWID")

        db.commit()

        while True:
            try:
                # Read queue
                item = self.queue.get()

                # Look for the end
                if item is None:
                    break

                # noinspection PyBroadException
                try:
                    # Unpack item
                    stage, bundle = item
                    self.process_item(db, stage, bundle)
                    db.commit()
                except:
                    db.rollback()

            except KeyboardInterrupt:
                pass

    def process_item(self, db: sqlite3.Connection, stage: str, bundle: TransactionBundle):
        """
        Write the data to the database

        :param db: The database object
        :param stage: "pre" or "post"
        :param bundle: The transaction bundle
        """
        try:
            cur = db.cursor()
            identifiers = self.get_identifiers(bundle)
            cur.execute("INSERT OR IGNORE INTO clients(duid, duid_ll, interface_id, remote_id) VALUES (?, ?, ?, ?)",
                        (identifiers['duid'], identifiers['duid_ll'], identifiers['interface_id'],
                         identifiers['remote_id']))
        except sqlite3.DatabaseError:
            return

        if stage == 'pre':
            message = bundle.request
            wanted_options = self.log_request_options
            query = "UPDATE clients SET last_request_transaction=?, last_request_type=?, " \
                    "last_request_ts=CURRENT_TIMESTAMP, last_request_options=? " \
                    "WHERE duid=? AND interface_id=? AND remote_id=?"
        elif stage == 'post':
            message = bundle.response
            wanted_options = self.log_response_options
            query = "UPDATE clients SET last_response_transaction=?, last_response_type=?, " \
                    "last_response_ts=CURRENT_TIMESTAMP, last_response_options=? " \
                    "WHERE duid=? AND interface_id=? AND remote_id=?"
        else:
            return

        # Process the data
        transaction_id = codecs.encode(message.transaction_id, 'hex').decode('ascii')
        message_type = camelcase_to_dash(message.__class__.__name__)
        if message_type.endswith('-message'):
            message_type = message_type[:-8]
        options = self.get_options_json(message.options, wanted_options)

        try:
            cur.execute(query, (transaction_id, message_type, options, identifiers['duid'], identifiers['interface_id'],
                                identifiers['remote_id']))
        except sqlite3.DatabaseError:
            return

    @staticmethod
    def get_identifiers(bundle: TransactionBundle) -> dict:
        """
        Extract interesting identifiers from the incoming message

        :param bundle: The transaction bundle
        :return: A dictionary of identifiers
        """
        # Get the DUID and create representations for in the database
        duid_obj = bundle.request.get_option_of_type(ClientIdOption).duid
        duid_ll = codecs.encode(getattr(duid_obj, 'link_layer_address', b''), 'hex').decode('ascii')
        if getattr(duid_obj, 'hardware_type') == 1:
            duid_ll = ':'.join([duid_ll[i:i + 2] for i in range(0, len(duid_ll), 2)])
        elif duid_ll:
            duid_ll = '0x' + duid_ll
        duid = '0x' + codecs.encode(duid_obj.save(), 'hex').decode('ascii')

        # Get the Interface ID and create representation for in the database
        interface_id_obj = bundle.incoming_relay_messages[0].get_option_of_type(InterfaceIdOption)
        if interface_id_obj:
            try:
                interface_id = interface_id_obj.interface_id.decode('ascii')
            except ValueError:
                interface_id = '0x' + codecs.encode(interface_id_obj.interface_id, 'hex').decode('ascii')
        else:
            interface_id = ''

        # Get the Remote ID and create representation for in the database
        remote_id_obj = bundle.incoming_relay_messages[0].get_option_of_type(RemoteIdOption)
        if remote_id_obj:
            try:
                remote_id = '{}:{}'.format(remote_id_obj.enterprise_number, remote_id_obj.remote_id.decode('ascii'))
            except ValueError:
                remote_id = '{}:0x{}'.format(remote_id_obj.enterprise_number,
                                             codecs.encode(remote_id_obj.remote_id, 'hex').decode('ascii'))
        else:
            remote_id = ''

        return {'duid': duid,
                'duid_ll': duid_ll,
                'interface_id': interface_id,
                'remote_id': remote_id}
