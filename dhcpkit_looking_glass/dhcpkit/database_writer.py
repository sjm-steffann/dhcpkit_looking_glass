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

ctx = multiprocessing.get_context('spawn')


class DatabaseProcess(ctx.Process):
    """
    Separate process for writing looking glass data to the database.
    """

    def __init__(self, filename):
        super().__init__()

        self.daemon = True
        self.queue = ctx.Queue(maxsize=1000)
        self.filename = filename

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
                    "  id INTEGER NOT NULL PRIMARY KEY, "

                    "  duid TEXT NOT NULL, "
                    "  interface_id TEXT NOT NULL, "
                    "  remote_id TEXT NOT NULL, "

                    "  last_request TEXT, "
                    "  last_request_ll VARCHAR(39), "
                    "  last_request_ts DATETIME, "

                    "  last_response TEXT, "
                    "  last_response_ts DATETIME, "

                    "  UNIQUE(duid, interface_id, remote_id)"
                    ")")

        # Do migrations if necessary
        cur.execute("PRAGMA USER_VERSION")
        last_version = cur.fetchone()[0]

        if last_version < 1:
            # Update to version 1
            cur.execute("ALTER TABLE clients ADD COLUMN last_request_type VARCHAR(50)")
            cur.execute("ALTER TABLE clients ADD COLUMN last_response_type VARCHAR(50)")
            last_version = 1

        cur.execute("PRAGMA USER_VERSION = {}".format(last_version))

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
            cur.execute("INSERT OR IGNORE INTO clients(duid, interface_id, remote_id) VALUES (?, ?, ?)",
                        (identifiers['duid'], identifiers['interface_id'], identifiers['remote_id']))
        except sqlite3.DatabaseError:
            return

        try:
            if stage == 'pre':
                message_type = bundle.request.__class__.__name__
                if message_type.endswith('Message'):
                    message_type = message_type[:-7]

                cur.execute("UPDATE clients "
                            "SET last_request_type=?, last_request=?, last_request_ll=?, "
                            "    last_request_ts=CURRENT_TIMESTAMP "
                            "WHERE duid=? AND interface_id=? AND remote_id=?",
                            (message_type, json.dumps(bundle.request, cls=JSONProtocolElementEncoder),
                             identifiers['link_local'],
                             identifiers['duid'], identifiers['interface_id'], identifiers['remote_id']))

            elif stage == 'post':
                message_type = bundle.response.__class__.__name__
                if message_type.endswith('Message'):
                    message_type = message_type[:-7]

                cur.execute("UPDATE clients "
                            "SET last_response_type=?, last_response=?, last_response_ts=CURRENT_TIMESTAMP "
                            "WHERE duid=? AND interface_id=? AND remote_id=?",
                            (message_type, json.dumps(bundle.response, cls=JSONProtocolElementEncoder),
                             identifiers['duid'], identifiers['interface_id'], identifiers['remote_id']))

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
        duid = '0x' + codecs.encode(duid_obj.save(), 'hex').decode('ascii')

        # Get the link-local address of the client
        link_local = str(bundle.incoming_relay_messages[0].peer_address)

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

        return {
            'duid': duid,
            'interface_id': interface_id,
            'remote_id': remote_id,
            'link_local': link_local,
        }
