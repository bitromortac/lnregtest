"""
Network components for the bitcoin/lightning regtest network.
"""
from abc import ABC, abstractmethod
import subprocess
import shutil
import time
import os
import os.path
import logging
import pathlib
import threading
from typing import Optional, List, NamedTuple
import re

from .node_config_templates import (
    lnd_config_template,
    bitcoind_config_template
)
from lnregtest.lib.utils import decode_byte_string_to_dict_or_str, convert_short_channel_id_to_channel_id, bfh

from lnregtest.lib.common import WAIT_SYNC_BITCOIND, WAIT_SYNC_ELECTRUMX

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ChannelState(NamedTuple):
    capacity: int
    channel_id: int
    commit_fee: int
    funding_txid: str
    initiator: bool
    local_balance: int
    outpoint: int
    remote_balance: int
    remote_pubkey: str
    state: str


class Graph(NamedTuple):
    funding_txid: str
    outpoint: int
    state: str


class ChannelInfo(NamedTuple):
    channel_id: int
    node1_key: str
    node2_key: str


def log_subprocess_output(pipe, prefix=''):
    for line in iter(pipe.readline, b''):  # b'\n'-separated lines
        if prefix:
            logger.debug(f'{prefix}: {str(line)}')
        else:
            logger.debug(f'{str(line)}')


class Bitcoind(object):
    """
    Bitcoind node abstraction.
    """

    def __init__(self, nodedata_folder: str,
                 binary_folder: Optional[str] = None):
        """
        :param nodedata_folder: str:
            absolute path to folder, where node data is stored
        :param binary_folder: str:
            absolute path where bitcoind/bitcoin-cli can be found, else
            binaries are taken from $PATH
        """
        self.nodedata_folder = nodedata_folder
        self.bitcoind_config_file = \
            os.path.join(self.nodedata_folder, 'bitcoin/bitcoin.conf')
        self.bitcoind_data_dir = os.path.join(self.nodedata_folder, 'bitcoin')

        # take binaries from path, if no binary folder is given
        if binary_folder is None:
            binary_folder = ''
        self.bitcoind_binary = os.path.join(binary_folder, 'bitcoind')
        self.bitcoincli_binary = os.path.join(binary_folder, 'bitcoin-cli')

        if shutil.which(self.bitcoind_binary) is None:
            raise FileNotFoundError(
                f"bitcoind executable not found: {self.bitcoind_binary}")
        if shutil.which(self.bitcoincli_binary) is None:
            raise FileNotFoundError(
                f"bitcoin-cli executable not found: {self.bitcoincli_binary}")

        self.bitcoind_process = None

    def start(self, from_scratch=True):
        """
        Gets bitcoind going.

        `from_scratch` determines, if the network should be built from a clean
        state.

        :param from_scratch: bool
        """

        # prepare data directories
        if from_scratch:
            self.clear_directory()
            self.setup_bitcoinddir()
        else:
            if not os.path.isdir(self.bitcoind_data_dir):
                raise FileNotFoundError(
                    'Bitcoind data directory not found '
                    '(from_scratch = False).')

        # start and wait
        self.start_bitcoind_process()
        self.block_until_started()
        logger.info("BTC: Bitcoind started.")

    def setup_bitcoinddir(self):
        """
        Sets up the bitcoind data folder.
        """
        pathlib.Path(self.bitcoind_data_dir).mkdir(parents=True, exist_ok=True)
        config = bitcoind_config_template

        with open(self.bitcoind_config_file, 'w') as f:
            f.write(config)

    def start_bitcoind_process(self):
        """
        Starts a bitcoind subprocess.
        """
        command = [self.bitcoind_binary,
                   '-datadir=' + self.bitcoind_data_dir]

        logger.info("BTC: Starting bitcoind.")
        logger.info(' '.join(command))
        self.bitcoind_process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def stop(self):
        self.bitcoincli(['stop'])
        logger.info("BTC: stopped bitcoind")
        # should wait for the process to really stop
        self.bitcoind_process.communicate()

    def block_until_started(self):
        """
        Checks, if bitcoind has started by looking at the cli response and
        blocks if it doesn't get proper response.
        """
        while True:
            result = self.bitcoincli(['getblockchaininfo'])
            started = True if result.returncode == 0 else False
            if started:
                break
            time.sleep(WAIT_SYNC_BITCOIND)

    def clear_directory(self):
        """
        Deletes the bitcoind regtest folder.
        """
        logger.debug("BTC: Cleaning up bitcoin data directory.")
        try:
            shutil.rmtree(self.bitcoind_data_dir)
        except FileNotFoundError as e:
            logger.debug("BTC: Directory already clean. %s", e)

    def bitcoincli(self, command):
        """
        Invokes the bitcoin-cli command line interface.

        :param command: list, contains CLI parameters
        :return: subprocess
        """
        cmd = [self.bitcoincli_binary, '-datadir=' +
               self.bitcoind_data_dir] + command
        logger.debug(' '.join(cmd))
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Handle errors of the bitcoin-cli call. Errors are expected
        # to occur for getblockchaininfo when the daemon is not ready to
        # take calls, therefore we exclude this case here.
        if command[0] != 'getblockchaininfo' and proc.returncode != 0:
            raise ChildProcessError(proc.stderr)

        return proc

    def getblockchaininfo(self):
        proc = self.bitcoincli(['getblockchaininfo'])
        return decode_byte_string_to_dict_or_str(proc.stdout)

    def get_blockheight(self):
        blockchaininfo = self.getblockchaininfo()
        return blockchaininfo['blocks']

    def mine_blocks(self, number_of_blocks):
        """
        Mines some blocks.

        :param number_of_blocks: int
        """
        logger.info("BTC: Mining %d blocks.", number_of_blocks)
        address = self.newaddress()
        command = list(['generatetoaddress', str(number_of_blocks), address])
        result = self.bitcoincli(command)
        logger.debug("BTC: Mined to address %s.", result.stdout)

    def fill_addresses(self, number_of_addresses):
        """
        Generates several addresses and attaches UTXOs to them.

        :param number_of_addresses: int
        """
        for _ in range(number_of_addresses):
            address = self.newaddress()
            command = list(['generatetoaddress', str(1), address])
            result = self.bitcoincli(command)
            logger.info("BTC: Mined to address %s.", result.stdout)

    def sendtoaddress(self, address, amount):
        """
        Sends funds to a given address.

        :param address: str
        :param amount: float: amount in BTC
        """
        proc = self.bitcoincli(['sendtoaddress', address, str(amount)])
        return decode_byte_string_to_dict_or_str(proc.stdout)

    def sendtoaddresses(self, addresses, amount):
        """
        Sends funds to given list of addresses.

        :param addresses: list of str
        :param amount: float: amount in BTC
        """
        logger.info("BTC: Sending funds to addresses.")
        for a in addresses:
            self.sendtoaddress(a, amount)

    def newaddress(self, address_type='bech32'):
        """
        Generates a new address.

        :param address_type: str: default is bech32
        :return: str: address
        """
        logger.debug("BTC: Getting new address.")
        command = ['getnewaddress', '', address_type]
        result = self.bitcoincli(command)
        address = result.stdout.strip()
        address = address.decode('utf-8')
        logger.debug("BTC: Generated new address %s.", address)
        return address

    def getbalances(self):
        """
        Gets confirmed and unconfirmed balances.

        :return: dict
        """
        logger.debug("BTC: Getting balances.")
        command = ['getbalances']
        result = self.bitcoincli(command)

        # convert into a dict
        balances = result.stdout.strip()
        balances = balances.decode('utf-8')
        balances = decode_byte_string_to_dict_or_str(balances)
        logger.debug("BTC: Generated new address %s.", balances)

        return balances


class ElectrumX(object):
    """
    Electrumx node abstraction.
    """

    def __init__(self, nodedata_folder: str,
                 binary_folder: Optional[str] = None):
        """
        :param nodedata_folder: str:
            absolute path to folder, where node data is stored
        :param binary_folder: str:
            absolute path where electrumx_server and electrumx_rpc can be found,
            else binaries are taken from $PATH
        """
        self.nodedata_folder = nodedata_folder
        self.db_directory = os.path.join(self.nodedata_folder, 'electrumx/db')
        self.services = "tcp://localhost:51001,rpc://localhost:8000"
        self.net = 'regtest'
        self.coin = 'BitcoinSegwit'
        self.daemon_url = "http://lnd:123456@localhost:18443"

        # export to environment variables
        os.environ['DB_DIRECTORY'] = self.db_directory
        os.environ['SERVICES'] = self.services
        os.environ['NET'] = self.net
        os.environ['COIN'] = self.coin
        os.environ['DAEMON_URL'] = self.daemon_url

        # take binaries from path, if no binary folder is given
        if binary_folder is None:
            binary_folder = ''
        self.server_binary = os.path.join(binary_folder, 'electrumx_server')
        self.rpc_binary = os.path.join(binary_folder, 'electrumx_rpc')

        if shutil.which(self.server_binary) is None:
            raise FileNotFoundError(
                f"electrumx_server executable not found: {self.server_binary}")
        if shutil.which(self.rpc_binary) is None:
            raise FileNotFoundError(
                f"electrumx_rpc executable not found: {self.rpc_binary}")

        self.server_process = None

    def start(self, from_scratch=True):
        """
        Gets electrumx going.

        `from_scratch` determines, if the network should be built from a clean
        state.

        :param from_scratch: bool
        """

        # prepare data directories
        if from_scratch:
            self.clear_directory()
            self.setup_db_dir()
        else:
            if not os.path.isdir(self.db_directory):
                raise FileNotFoundError(
                    'Electrumx database not found (from_scratch = False).')

        # start and wait
        self.start_process()
        self.block_until_started()
        logger.info("ETRX: Electrumx started.")

    def setup_db_dir(self):
        """
        Sets up the database folder.
        """
        pathlib.Path(self.db_directory).mkdir(parents=True, exist_ok=True)

    def start_process(self):
        """
        Starts an electrumx subprocess.
        """
        command = [self.server_binary]

        logger.info("ETRX: Starting electrumx.")
        self.server_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        # with self.server_process:
        #     log_subprocess_output(self.server_process.stdout)

    def stop(self):
        self.rpc(['stop'])
        logger.info("ETRX: stopping")
        # should wait for the process to really stop
        self.server_process.communicate()
        logger.info("ETRX: stopped")

    def block_until_started(self):
        """
        Checks, if bitcoind has started by looking at the cli response and
        blocks if it doesn't get proper response.
        """
        while True:
            result = self.rpc(['getinfo'])
            started = True if result.returncode == 0 else False
            if started:
                break
            time.sleep(WAIT_SYNC_BITCOIND)

    def clear_directory(self):
        """
        Deletes the database folder.
        """
        logger.debug("ETRX: Cleaning up the database directory.")
        try:
            shutil.rmtree(self.db_directory)
        except FileNotFoundError as e:
            logger.debug("ETRX: Directory already clean. %s", e)

    def rpc(self, command):
        """
        Invokes the electrumx rpc.

        :param command: list, contains CLI parameters
        :return: subprocess
        """
        cmd = [self.rpc_binary]
        cmd.extend(command)

        logger.debug(' '.join(cmd))
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        logger.debug(proc)

        return proc

    def getinfo(self):
        proc = self.rpc(['getinfo'])
        return decode_byte_string_to_dict_or_str(proc.stdout)


class LightningDaemon(ABC):
    # general attributes
    name: str
    lnport: int
    pubkey: Optional[str]
    node_properties: dict
    nodes_folder: str
    binary_folder: Optional[str]

    # lnd process
    server_process: Optional[subprocess.Popen]
    logs: List[str]
    logs_cond: threading.Condition
    running: bool
    thread: Optional[threading.Thread]
    server_binary: str
    rpc_command: List[str]

    # folders and binaries
    nodes_folder: str
    data_dir: str

    # fees
    base_fee_msat: int
    fee_rate: float

    def __init__(self, name, node_properties, nodes_folder,
                 binary_folder=None):
        """
        :param name: char: unique human readable identifier, e.g. A, B, ...
        :param node_properties: dict:
            as defined in network_definitions
        :param nodes_folder: str:
            absolute path to the node data folder
        :param binary_folder: str:
            absolute path to the binary folder, if not given, binaries are
            taken from $PATH
        """
        self.name = name
        self.lnport = node_properties['port']
        self.pubkey = None
        self.node_properties = node_properties

        # lnd process
        self.server_process = None
        self.logs = []
        self.logs_cond = threading.Condition(threading.RLock())
        self.running = False
        self.thread = None
        self.rpc_command = []

        # folders and binaries
        self.nodes_folder = nodes_folder
        self.data_dir = os.path.join(
            self.nodes_folder, 'lnnodes/' + self.name)

        # fees
        self.base_fee_msat = node_properties['base_fee_msat']
        self.fee_rate = node_properties['fee_rate']

    # following code was taken from github.com/cdecker/lightning-integration
    def tail(self):
        """Tail the stdout of the process and remember it.
        Stores the lines of output produced by the process in
        self.logs and signals that a new line was read so that it can
        be picked up by consumers.
        """
        try:
            for line in iter(self.server_process.stdout.readline, ''):
                if len(line) == 0:
                    break
                with self.logs_cond:
                    self.logs.append(str(line.rstrip()))
                    self.logs_cond.notifyAll()
        except ValueError:
            self.running = False

    def wait_for_log(self, regex, offset=1000, timeout=60):
        """Look for `regex` in the logs.
        We tail the stdout of the process and look for `regex`,
        starting from `offset` lines in the past. We fail if the
        timeout is exceeded or if the underlying process exits before
        the `regex` was found. The reason we start `offset` lines in
        the past is so that we can issue a command and not miss its
        effects.
        """
        logger.debug("%s: Waiting for '%s' in the logs", self.name, regex)
        ex = re.compile(regex)
        start_time = time.time()
        pos = max(len(self.logs) - offset, 0)
        initial_pos = len(self.logs)
        while True:
            if time.time() > start_time + timeout:
                print("Can't find {} in logs".format(regex))
                with self.logs_cond:
                    for i in range(initial_pos, len(self.logs)):
                        print("  " + self.logs[i])
                if self.is_in_log(regex):
                    print("(Was previously in logs!")
                raise TimeoutError(
                    'Unable to find "{}" in logs.'.format(regex))
            elif not self.running:
                print('Logs: {}'.format(self.logs))
                raise ValueError('Process died while waiting for logs')

            with self.logs_cond:
                if pos >= len(self.logs):
                    self.logs_cond.wait(1)
                    continue

                if ex.search(self.logs[pos]):
                    logging.debug("%s: Found '%s' in logs", self.name, regex)
                    return self.logs[pos]
                pos += 1

    def is_in_log(self, regex):
        """Look for `regex` in the logs."""
        ex = re.compile(regex)
        for log in self.logs:
            if ex.search(log):
                logging.debug("Found '%s' in logs", regex)
                return True

        logging.debug("Did not find '%s' in logs", regex)
        return False

    @abstractmethod
    def start(self) -> subprocess.Popen:
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def print_rpc_command(self):
        pass

    @abstractmethod
    def setup_datadir(self):
        pass

    @abstractmethod
    def clear_directory(self):
        pass

    @abstractmethod
    def listchannels(self) -> List[ChannelState]:
        pass

    def rpc(self, command):
        """
        Invokes the rpc command line interface for the LN server.

        :param command: list of command line arguments
        :return:
            int: error code
            dict: generated from json response of cli
        """
        # make sure all arguments in list are str
        command = list(map(str, command))
        cmd = self.rpc_command + command
        logger.debug('%s: %s.', self.name, ' '.join(cmd))
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        dict_str = decode_byte_string_to_dict_or_str(proc.stdout)
        if proc.returncode:
            logger.error("%s: %s", self.name, proc.stderr)
        logger.debug("%s: %s", self.name, dict_str)

        return proc.returncode, dict_str


class LND(LightningDaemon):
    def __init__(self, name, node_properties, nodes_folder,
                 binary_folder=None):
        super().__init__(name, node_properties, nodes_folder, binary_folder)

        # network definitions
        self._grpc_port = node_properties['grpc_port']
        self._rest_port = node_properties['rest_port']
        self._grpc_host = 'localhost:' + str(self._grpc_port)

        # take binaries from path, if no binary folder is given
        if binary_folder is None:
            binary_folder = ''
        self.server_binary = os.path.join(binary_folder, 'lnd')
        self.rpc_binary = os.path.join(binary_folder, 'lncli')

        # check if executables can be found
        if shutil.which(self.server_binary) is None:
            raise FileNotFoundError(
                f"lnd executable not found: {self.server_binary}")
        if shutil.which(self.rpc_binary) is None:
            raise FileNotFoundError(
                f"lncli executable not found: {self.rpc_binary}")

        # file paths
        self._cert_file = os.path.join(self.data_dir, 'tls.cert')
        self._macaroon_file = os.path.join(
            self.data_dir, 'data/chain/bitcoin/regtest/admin.macaroon')
        self._lnd_config_file = os.path.join(self.data_dir, 'lnd.conf')

        # lncli
        self.rpc_command = [
            self.rpc_binary,
            '--lnddir=' + self.data_dir,
            '--rpcserver=' + str(self._grpc_host),
            '--macaroonpath=' + self._macaroon_file,
            '--network=regtest',
        ]

    def start(self, from_scratch=True):
        """
        Start an lnd node.

        :param from_scratch: bool
        :return:
        """

        if from_scratch:
            self.clear_directory()
            self.setup_datadir()
        else:
            if not os.path.isdir(self.data_dir):
                raise FileNotFoundError(
                    '{}: Lnd data directory not found '
                    '(from_scratch = False).'.format(self.name))

        command = [self.server_binary,
                   '--trickledelay=1',
                   '--lnddir=' + self.data_dir,
                   '--noseedbackup']

        cmd = ' '.join(command)
        logger.info("%s: Starting lnd: %s ", self.name, cmd)

        self.thread = threading.Thread(target=self.tail)
        self.thread.daemon = False

        # we start nonblocking with Popen
        self.server_process = subprocess.Popen(command, stdout=subprocess.PIPE)
        self.thread.start()
        self.running = True

        # we consider lnd to be started, when it has scanned the chain
        self.wait_for_log("Finished rescan")

        return self.server_process

    def stop(self):
        self.rpc(['stop'])
        logger.info('%s: stopped lnd', self.name)
        # should wait for the process to really stop
        self.server_process.communicate()
        # TODO: if this fails, force stop

    def print_rpc_command(self):
        """
        Prints the lncli command to use in the shell for testing.
        """
        cmd = ' '.join(self.rpc_command)
        logger.info("%s:", self.name)
        logger.info(cmd)

    def setup_datadir(self):
        """
        Sets up the lnd data folder.
        """
        pathlib.Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        config = lnd_config_template.format(
            name=self.name,
            lnd_port=self.lnport,
            rest_port=self._rest_port,
            rpc_port=self._grpc_port,
            base_fee_msat=self.base_fee_msat,
            fee_rate=int(1E6 * self.fee_rate),
        )

        with open(self._lnd_config_file, 'w') as f:
            f.write(config)

    def clear_directory(self):
        """
        Deletes the lnd data directory of this node.
        """
        logger.debug("%s: Cleaning up lnd data directory.", self.name)
        try:
            shutil.rmtree(self.data_dir)
        except FileNotFoundError:
            logger.debug("%s: Directory already clean.", self.name)

    def getinfo(self):
        returncode, info = self.rpc(['getinfo'])
        return info

    def getaddress(self):
        returncode, address = self.rpc(['newaddress', 'p2wkh'])
        return address['address']

    def _connect(self, pubkey, host):
        logger.info("%s: Connecting to %s", self.name, pubkey)
        address = pubkey + '@' + host
        returncode, info = self.rpc(['connect', address])
        return info

    def _openchannel(self, pubkey, local_sat, remote_sat):
        logger.info("%s: Open channel to %s", self.name, pubkey)
        command = ['openchannel', '--min_confs', '0', pubkey, local_sat,
                   remote_sat]
        returncode, info = self.rpc(command)
        return info

    def connect_and_openchannel(self, pubkey, host, local_sat, remote_sat):
        self._connect(pubkey, host)
        info = self._openchannel(pubkey, local_sat, remote_sat)
        funding_txid = info['funding_txid']
        return funding_txid

    def disconnect(self, pubkey):
        logger.info("%s: Disconnecting %s.", self.name, pubkey)
        command = ['disconnect', pubkey]
        returncode, info = self.rpc(command)
        return info

    def set_node_pubkey(self):
        info = self.getinfo()
        logger.info(
            "%s: setting node public key to %s",
            self.name, info['identity_pubkey'])
        self.pubkey = info['identity_pubkey']

    def listchannels(self) -> List[ChannelState]:
        command = ['listchannels']
        _, channels = self.rpc(command)
        channel_states = []
        for c in channels['channels']:
            funding_txid, outpoint = c['channel_point'].split(':')
            channel_states.append(ChannelState(
                capacity=c['capacity'],
                channel_id=c['chan_id'],
                commit_fee=c['commit_fee'],
                funding_txid=funding_txid,
                initiator=c['initiator'],
                local_balance=c['local_balance'],
                outpoint=int(outpoint),
                remote_balance=c['remote_balance'],
                remote_pubkey=c['remote_pubkey'],
                state='OPEN' if c['active'] else 'OPENING',
            ))
        return channel_states

    def updatechanpolicy(self, base_fee_msat, fee_rate, time_lock_delta=20,
                         channel_point=None):
        command = [
            'updatechanpolicy', int(base_fee_msat), fee_rate, time_lock_delta]
        if channel_point:
            command += channel_point
        returncode, info = self.rpc(command)
        return info

    def getnetworkinfo(self):
        command = ['getnetworkinfo']
        _, networkinfo = self.rpc(command)
        return networkinfo

    def describegraph(self) -> List[ChannelInfo]:
        command = ['describegraph']
        _, networkinfo = self.rpc(command)
        channels = []
        for c in networkinfo['edges']:
            # construct channel info
            channel_info = ChannelInfo(node1_key=c['node1_pub'], node2_key=c['node2_pub'],
                                       channel_id=int(c['channel_id']))
            channels.append(channel_info)
        return channels

    def walletbalance(self):
        command = ['walletbalance']
        _, walletbalance = self.rpc(command)
        return walletbalance


class Electrum(LightningDaemon):
    def __init__(self, name: str, node_properties: dict, nodes_folder: str,
                 binary_folder: Optional[str] = None):
        super().__init__(name, node_properties, nodes_folder, binary_folder)
        self.name = name

        # network definitions
        self.lnport = node_properties['port']

        # fees
        self.base_fee_msat = node_properties['base_fee_msat']
        self.fee_rate = node_properties['fee_rate']

        # take binaries from path, if no binary folder is given
        if binary_folder is None:
            binary_folder = ''
        self.server_binary = os.path.join(binary_folder, 'electrum')
        self.client_binary = os.path.join(binary_folder, 'electrum')

        # check if executables can be found
        if shutil.which(self.server_binary) is None:
            raise FileNotFoundError(
                f"electrum executable not found: {self.server_binary}")

        # rpc command
        self.rpc_command = [
            self.client_binary,
            '-v',
            '-D' + self.data_dir,
            '--regtest',
        ]

    def start(self, from_scratch=True):
        """
        Start an electrum node.

        :param from_scratch: bool
        :return:
        """

        if from_scratch:
            self.clear_directory()
            self.setup_datadir()
        else:
            if not os.path.isdir(self.data_dir):
                raise FileNotFoundError(
                    '{}: Electrum data directory not found '
                    '(from_scratch = False).'.format(self.name))

        logger.info("%s: Configuring electrum.", self.name)

        self.rpc(['--offline', 'create'])
        self.rpc(['--offline', 'setconfig', 'log_to_file', 'true'])
        self.rpc(['--offline', 'setconfig', 'lightning_listen',
                  'localhost:' + str(self.lnport)])
        self.rpc(['--offline', 'setconfig', 'oneserver', 'true'])
        self.rpc(['--offline', 'setconfig', 'server', '127.0.0.1:51001:t'])

        logger.info("%s: Starting electrum.", self.name)
        self.thread = threading.Thread(target=self.tail)
        self.thread.daemon = False

        # we start nonblocking with Popen
        daemon_command = [
            self.server_binary,
            '-v',
            '-D' + self.data_dir,
            '--regtest',
            'daemon',
        ]
        self.server_process = subprocess.Popen(
            daemon_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.thread.start()
        self.running = True

        # we consider lnd to be started, when it has scanned the chain
        self.wait_for_log("connection established")
        self.rpc(['load_wallet'])

        return self.server_process

    def stop(self):
        self.rpc(['stop'])
        logger.info('%s: stopped electrum', self.name)
        # should wait for the process to really stop
        self.server_process.communicate()
        # TODO: if this fails, force stop

    def print_rpc_command(self):
        """
        Prints the rpc command to use in the shell for testing.
        """
        cmd = ' '.join(self.rpc_command)
        logger.info("%s:", self.name)
        logger.info(cmd)

    def setup_datadir(self):
        """
        Sets up the lnd data folder.
        """
        pathlib.Path(self.data_dir).mkdir(parents=True, exist_ok=True)

    def clear_directory(self):
        """
        Deletes the electrum data directory of this node.
    """
        logger.debug("%s: Cleaning up lnd data directory.", self.name)
        try:
            shutil.rmtree(self.data_dir)
        except FileNotFoundError:
            logger.debug("%s: Directory already clean.", self.name)

    def getinfo(self):
        returncode, info = self.rpc(['getinfo'])
        return info

    def getaddress(self):
        returncode, address = self.rpc(['getunusedaddress'])
        return address

    def connect_and_openchannel(self, pubkey, host, local_sat, remote_sat) -> str:
        self._wait_for_funds((local_sat + remote_sat) / 1E8)
        logger.info("%s: Open channel to %s@%s", self.name, pubkey, host)
        command = ['open_channel', '--push_amount', remote_sat / 1E8,
                   f"{pubkey}@{host}", local_sat / 1E8]
        returncode, info = self.rpc(command)
        funding_txid = info.split(':')[0]
        return funding_txid

    def _wait_for_funds(self, amount_btc: float):
        logger.info(f"{self.name}: waiting for funds")
        while True:
            time.sleep(0.5)
            _, balance = self.rpc(['getbalance'])
            if float(balance['confirmed']) > 0 and balance.get('unconfirmed', None) is None:
                break

    def wait_all_channels_open(self):
        while True:
            logger.info(f"{self.name}: waiting for channels to be open")
            time.sleep(1.0)
            channel_states = self.listchannels()
            try:
                for c in channel_states:
                    # if not all channels are open, wait
                    if c.state != 'OPEN':
                        raise Exception
            except:
                continue

            # all channels are open
            logger.info(f"{self.name}: all channels open")
            return

    @property
    def nodeid(self) -> str:
        proc, connection_string = self.rpc(['nodeid'])
        nodeid = connection_string.split('@')[0]
        return nodeid

    def set_node_pubkey(self):
        node_pubkey = self.nodeid
        logger.info(
            "%s: setting node public key to %s",
            self.name, node_pubkey)
        self.pubkey = node_pubkey

    def listchannels(self) -> List[ChannelState]:
        command = ['list_channels']
        _, channels = self.rpc(command)
        channel_states = []
        for c in channels:
            # convert the electrum notation of the short channel id to
            # the integer representation
            try:
                block, trans, out = map(int, c['short_channel_id'].split('x'))
                chan_id = convert_short_channel_id_to_channel_id(block, trans, out)
            except AttributeError:
                chan_id = None

            funding_txid, outpoint = c['channel_point'].split(':')
            channel_states.append(ChannelState(
                capacity=c['local_balance'] + c['remote_balance'],
                channel_id=chan_id,
                commit_fee=0,  # TODO: expose commit fee in electrum
                funding_txid=funding_txid,
                initiator=True,  # TODO: expose initiator in electrum
                local_balance=c['local_balance'],
                outpoint=int(outpoint),
                state=c['state'],
                remote_balance=c['remote_balance'],
                remote_pubkey=c['remote_pubkey']
            ))
        return channel_states

    def updatechanpolicy(self, base_fee_msat, fee_rate, time_lock_delta=20,
                         channel_point=None):
        command = [
            'updatechanpolicy', int(base_fee_msat), fee_rate, time_lock_delta]
        if channel_point:
            command += channel_point
        returncode, info = self.rpc(command)
        return info

    def getnetworkinfo(self):
        command = ['getnetworkinfo']
        _, networkinfo = self.rpc(command)
        return networkinfo

    def describegraph(self) -> List[ChannelInfo]:
        command = ['dumpgraph']
        _, networkinfo = self.rpc(command)
        channels = []
        for c in networkinfo['channels']:
            # convert short channel id to channel id
            cid: str = c['short_channel_id']
            cid: bytes = bfh(cid)
            blockheight = int.from_bytes(cid[:3], byteorder='big')
            transaction = int.from_bytes(cid[3:6], byteorder='big')
            output = int.from_bytes(cid[6:8], byteorder='big')
            channel_id = convert_short_channel_id_to_channel_id(
                blockheight, transaction, output)

            # construct channel info
            channel_info = ChannelInfo(node1_key=c['node1_id'], node2_key=c['node2_id'], channel_id=channel_id)
            channels.append(channel_info)
        return channels

    def walletbalance(self):
        command = ['walletbalance']
        _, walletbalance = self.rpc(command)
        return walletbalance
