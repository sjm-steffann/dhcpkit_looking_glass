"""
This option handler provides a looking glass into DHCP server operations
"""
import configparser
import logging
from queue import Full

from dhcpkit.ipv6.option_handlers import OptionHandler
from dhcpkit.ipv6.transaction_bundle import TransactionBundle

from dhcpkit_looking_glass.dhcpkit.database_writer import DatabaseProcess

logger = logging.getLogger(__name__)


class LookingGlassOptionHandler(OptionHandler):
    """
    Option handler that provides a looking glass into DHCP server operations by logging information about requests
    and responses into an SQLite database.

    The primary key is (duid, interface_id, remote_id)
    """

    def __init__(self, filename: str):
        super().__init__()

        self._worker = DatabaseProcess(filename)
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

        return cls(status_filename)

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
