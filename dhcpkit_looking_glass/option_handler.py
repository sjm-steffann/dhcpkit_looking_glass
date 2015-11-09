"""
This option handler provides a looking glass into DHCP server operations
"""
import configparser
import logging
from queue import Full

from dhcpkit.ipv6.option_handlers import OptionHandler
from dhcpkit.ipv6.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class LookingGlassOptionHandler(OptionHandler):
    """
    Option handler that provides a looking glass into DHCP server operations by logging information about requests
    and responses into an SQLite database. The database has the following structure:

    A table `requests`:
    - duid: the full DUID of the client in hex
    - duid_ll: the link-layer address from the DUID in hex, if any
    - interface_id: the interface-id reported by the relay closest to the client as string or hex
    - remote_id: the remote-id reported by the relay closest to the client as string or hex
    - last_transaction_id: the transaction ID from the last request from the client
    - last_request_type: the message type of the last request from the client
    - last_request_ts: timestamp of the last request from the client
    - last_request_options: a JSON representation of the options in the last request from the client

    A table `responses`:
    - duid: the full DUID of the client in hex
    - duid_ll: the link-layer address from the DUID in hex, if any
    - interface_id: the interface-id reported by the relay closest to the client as string or hex
    - remote_id: the remote-id reported by the relay closest to the client as string or hex
    - last_transaction_id: the transaction ID from the last response from the client
    - last_response_type: the message type of the last response from the server
    - last_response_ts: timestamp of the last response from the server
    - last_response_options: a JSON representation of the options in the last response from the server

    The primary key of both tables is (duid, interface_id, remote_id)
    """

    def __init__(self, filename: str, log_request_options: list = None, log_response_options: list = None):
        super().__init__()

        self._worker = DatabaseProcess(filename, log_request_options, log_response_options)
        self._worker.start()

    def __del__(self):
        """
        Clean up when this option handler is being removed (or reloaded)
        """
        logger.debug("Deleting {}".format(self.__class__.__name__))

        # Signal that we are shutting down
        self._worker.queue.put(None)

        # And wait for the thread to finish
        self._worker.join(timeout=5)
        if self._worker.is_alive():
            logger.error("LookingGlass database writer has not shut down, thread may be hanging")

        logger.debug("Deleted {}".format(self.__class__.__name__))

    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str = None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        status_filename = section.get('status-file')
        if not status_filename:
            raise configparser.NoOptionError('status-file', section.name)

        return cls(status_filename, ['option-request', 'iana', 'iapd'], ['iana', 'iapd'])

    def pre(self, bundle: TransactionBundle):
        """
        Log the request before we start processing it.

        :param bundle: The transaction bundle
        """
        try:
            self._worker.queue.put(('pre', bundle), block=False)
        except Full:
            logger.warning("Not logging transaction in LookingGlass: queue is full")

    def handle(self, bundle: TransactionBundle):
        """
        We log in pre() and post. We don't do anything interesting here.

        :param bundle: The transaction bundle
        """
        pass

    def post(self, bundle: TransactionBundle):
        """
        Log the response before we send it to the client.

        :param bundle: The transaction bundle
        """
        try:
            self._worker.queue.put(('post', bundle), block=False)
        except Full:
            logger.warning("Not logging transaction in LookingGlass: queue is full")
