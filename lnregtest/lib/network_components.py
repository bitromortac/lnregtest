"""
Network components for the bitcoin/lightning regtest network.
"""
import subprocess
import shutil
import time
import os.path
import logging
import pathlib
import threading
import re

from .node_config_templates import (
    lnd_config_template,
    bitcoind_config_template
)
from lnregtest.lib.utils import decode_byte_string_to_dict

from lnregtest.lib.common import WAIT_SYNC_BITCOIND

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class RegTestBitcoind(object):
    """
    Bitcoind node abstraction.
    """
    def __init__(self, nodedata_folder, binary_folder=None):
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
        return decode_byte_string_to_dict(proc.stdout)

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
        return decode_byte_string_to_dict(proc.stdout)

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
        balances = decode_byte_string_to_dict(balances)
        logger.debug("BTC: Generated new address %s.", balances)

        return balances


class RegTestLND(object):
    """LND node abstraction."""
    def __init__(self, name, node_properties, nodedata_folder,
                 binary_folder=None):
        """
        :param name: char: unique human readable identifier, e.g. A, B, ...
        :param node_properties: dict:
            as defined in network_definitions
        :param nodedata_folder: str:
            absolute path to the node data folder
        :param binary_folder: str:
            absolute path to the binary folder, if not given, binaries are
            taken from $PATH
        """
        self.name = name

        # network definitions
        self.lndport = node_properties['port']
        self.grpc_port = node_properties['grpc_port']
        self.restport = node_properties['rest_port']
        self.grpc_host = 'localhost:' + str(self.grpc_port)

        # fees
        self.base_fee_msat = node_properties['base_fee_msat']
        self.fee_rate = node_properties['fee_rate']

        self.version = None
        self.pubkey = None

        # lnd process
        self.lnd_process = None
        self.logs = []
        self.logs_cond = threading.Condition(threading.RLock())
        self.running = False
        self.thread = None

        # take binaries from path, if no binary folder is given
        if binary_folder is None:
            binary_folder = ''
        self.lnd_binary = os.path.join(binary_folder, 'lnd')
        self.lncli_binary = os.path.join(binary_folder, 'lncli')

        # check if executables can be found
        if shutil.which(self.lnd_binary) is None:
            raise FileNotFoundError(
                f"lnd executable not found: {self.lnd_binary}")
        if shutil.which(self.lncli_binary) is None:
            raise FileNotFoundError(
                f"lncli executable not found: {self.lncli_binary}")

        # file paths
        self.nodedata_folder = nodedata_folder
        self.lnd_data_dir = os.path.join(
            self.nodedata_folder, 'lndnodes/' + self.name)
        self.cert_file = os.path.join(self.lnd_data_dir, 'tls.cert')
        self.macaroon_file = os.path.join(
            self.lnd_data_dir, 'data/chain/bitcoin/regtest/admin.macaroon')
        self.lnd_config_file = os.path.join(self.lnd_data_dir, 'lnd.conf')

        # lncli
        self.lncli_command = [
            self.lncli_binary,
            '--lnddir=' + self.lnd_data_dir,
            '--rpcserver=' + str(self.grpc_host),
            '--macaroonpath=' + self.macaroon_file,
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
            self.setup_lnddir()
        else:
            if not os.path.isdir(self.nodedata_folder):
                raise FileNotFoundError(
                    '{}: Lnd data directory not found '
                    '(from_scratch = False).'.format(self.name))

        command = [self.lnd_binary,
                   '--trickledelay=1',
                   '--lnddir=' + self.lnd_data_dir,
                   '--noseedbackup']

        cmd = ' '.join(command)
        logger.info("%s: Starting lnd: %s ", self.name, cmd)

        self.thread = threading.Thread(target=self.tail)
        self.thread.daemon = False

        # we start nonblocking with Popen
        self.lnd_process = subprocess.Popen(command, stdout=subprocess.PIPE)
        self.thread.start()
        self.running = True

        # we consider lnd to be started, when it has scanned the chain
        self.wait_for_log("Finished rescan")

        return self.lnd_process

    # following code was taken from github.com/cdecker/lightning-integration
    def tail(self):
        """Tail the stdout of the process and remember it.
        Stores the lines of output produced by the process in
        self.logs and signals that a new line was read so that it can
        be picked up by consumers.
        """
        try:
            for line in iter(self.lnd_process.stdout.readline, ''):
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

    def stop(self):
        self.lncli(['stop'])
        logger.info('%s: stopped lnd', self.name)
        # should wait for the process to really stop
        self.lnd_process.communicate()
        # TODO: if this fails, force stop

    def lncli(self, command):
        """
        Invokes the lncli command line interface for lnd.

        :param command: list of command line arguments
        :return:
            int: error code
            dict: generated from json response of cli
        """
        # make sure all arguments in list are str
        command = list(map(str, command))
        cmd = self.lncli_command + command
        logger.debug('%s: %s.', self.name, ' '.join(cmd))
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout_dict = decode_byte_string_to_dict(proc.stdout)
        if proc.returncode:
            logger.error("%s: %s", self.name, proc.stderr)
        logger.debug("%s: %s", self.name, stdout_dict)

        return proc.returncode, stdout_dict

    def print_lncli_command(self):
        """
        Prints the lncli command to use in the shell for testing.
        """
        cmd = ' '.join(self.lncli_command)
        logger.info("%s:", self.name)
        logger.info(cmd)

    def setup_lnddir(self):
        """
        Sets up the lnd data folder.
        """
        pathlib.Path(self.lnd_data_dir).mkdir(parents=True, exist_ok=True)
        config = lnd_config_template.format(
            name=self.name,
            lnd_port=self.lndport,
            rest_port=self.restport,
            rpc_port=self.grpc_port,
            base_fee_msat=self.base_fee_msat,
            fee_rate=int(1E6 * self.fee_rate),
        )

        with open(self.lnd_config_file, 'w') as f:
            f.write(config)

    def clear_directory(self):
        """
        Deletes the lnd data directory of this node.
        """
        logger.debug("%s: Cleaning up lnd data directory.", self.name)
        try:
            shutil.rmtree(self.lnd_data_dir)
        except FileNotFoundError:
            logger.debug("%s: Directory already clean.", self.name)

    def getinfo(self):
        returncode, info = self.lncli(['getinfo'])
        return info

    def getaddress(self):
        returncode, address = self.lncli(['newaddress', 'p2wkh'])
        return address

    def connect(self, pubkey, host):
        logger.info("%s: Connecting to %s", self.name, pubkey)
        address = pubkey + '@' + host
        returncode, info = self.lncli(['connect', address])
        return info

    def disconnect(self, pubkey):
        logger.info("%s: Disconnecting %s.", self.name, pubkey)
        command = ['disconnect', pubkey]
        returncode, info = self.lncli(command)
        return info

    def openchannel(self, pubkey, local_sat, remote_sat):
        logger.info("%s: Open channel to %s", self.name, pubkey)
        command = ['openchannel', '--min_confs', '0', pubkey, local_sat,
                   remote_sat]
        returncode, info = self.lncli(command)
        return info

    def set_node_pubkey(self):
        info = self.getinfo()
        logger.info(
            "%s: setting node public key to %s",
            self.name, info['identity_pubkey'])
        self.pubkey = info['identity_pubkey']

    def listchannels(self):
        command = ['listchannels']
        _, channels = self.lncli(command)
        return channels

    def updatechanpolicy(self, base_fee_msat, fee_rate, time_lock_delta=20,
                         channel_point=None):
        command = [
            'updatechanpolicy', int(base_fee_msat), fee_rate, time_lock_delta]
        if channel_point:
            command += channel_point
        returncode, info = self.lncli(command)
        return info

    def getnetworkinfo(self):
        command = ['getnetworkinfo']
        _, networkinfo = self.lncli(command)
        return networkinfo

    def describegraph(self):
        command = ['describegraph']
        _, networkinfo = self.lncli(command)
        return networkinfo

    def walletbalance(self):
        command = ['walletbalance']
        _, walletbalance = self.lncli(command)
        return walletbalance
