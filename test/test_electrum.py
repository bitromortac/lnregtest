import os
import sys
import tempfile
import time
import unittest
import warnings

from lnregtest.lib.network import Network
from lnregtest.lib.network_components import Electrum, ElectrumX, Bitcoind
from lnregtest.lib.utils import format_dict, dict_comparison
from lnregtest.lib.common import logger_config

import logging.config
logging.config.dictConfig(logger_config)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.handlers[0].setLevel(logging.DEBUG)

test_dir = os.path.dirname(os.path.realpath(__file__))
test_data_dir = os.path.join(test_dir, 'test_data')


class TestElectrumX(unittest.TestCase):
    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        logger.info(f"Testdir: {self.test_dir}")
        self.bitcoind = Bitcoind(self.test_dir)
        self.electrumx = ElectrumX(self.test_dir)

    def test_run(self):
        self.bitcoind.start()
        self.electrumx.start()
        time.sleep(1)
        self.electrumx.stop()
        self.bitcoind.stop()


class TestElectrum(unittest.TestCase):
    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        logger.info(f"Testdir: {self.test_dir}")
        self.bitcoind = Bitcoind(self.test_dir)
        self.electrumx = ElectrumX(self.test_dir)
        self.bitcoind.start()
        self.electrumx.start()

    def test_electrum(self):
        node_properties = {
            'port': 9735,
            'base_fee_msat': 10,
            'fee_rate': 0.0001,
        }
        self.electrum = Electrum('A', node_properties, self.test_dir)
        self.electrum.start()
        logger.info(self.electrum.getinfo())


    def tearDown(self) -> None:
        self.electrum.stop()
        self.electrumx.stop()
        self.bitcoind.stop()


class TestElectrumMasterNode(unittest.TestCase):
    def test_network_start(self):
        """
        Each node has a different view of the network, which is why the
        graph has to be assembled from all the nodes via the listchannels
        command.
        """
        graph_fixture = \
            {
                "A": {
                    "1": {
                        "remote_name": "B",
                        "capacity": 4000000,
                        "local_balance": 2105264,
                        "remote_balance": 1894736,
                        "commit_fee": 0,
                        "initiator": True
                    },
                    "2": {
                        "remote_name": "C",
                        "capacity": 5000000,
                        "local_balance": 2631579,
                        "remote_balance": 2368421,
                        "commit_fee": 0,
                        "initiator": True
                    }
                },
                "B": {
                    "3": {
                        "remote_name": "C",
                        "capacity": 100000,
                        "local_balance": 90950,
                        "remote_balance": 0,
                        "commit_fee": 9050,
                        "initiator": True
                    },
                    "1": {
                        "remote_name": "A",
                        "capacity": 4000000,
                        "local_balance": 1894736,
                        "remote_balance": 2072684,
                        "commit_fee": 32580,
                        "initiator": False
                    }
                },
                "C": {
                    "3": {
                        "remote_name": "B",
                        "capacity": 100000,
                        "local_balance": 0,
                        "remote_balance": 90950,
                        "commit_fee": 9050,
                        "initiator": False
                    },
                    "2": {
                        "remote_name": "A",
                        "capacity": 5000000,
                        "local_balance": 2368421,
                        "remote_balance": 2598999,
                        "commit_fee": 32580,
                        "initiator": False
                    }
                }
            }

        testnet = Network(
            network_definition_location='star_ring_electrum', from_scratch=True,
            node_limit='C')

        # this try-finally construct has to be employed to keep a network
        # running asynchronously, while accessing some of its properties
        try:
            testnet.run_nocleanup()
            graph_dict = testnet.assemble_graph()
            # to create a fixture, convert lower-case bool output to proper
            # python bools:
            logger.info("Complete assembled channel graph:")
            logger.info(format_dict(graph_dict))
            self.assertTrue(
                dict_comparison(graph_dict, graph_fixture, show_diff=True))
        finally:
            testnet.cleanup()


class TestRunFromBackground(unittest.TestCase):
    def dummy_test_run_from_background(self):
        """
        If you want to develop tests, you can run the network in the background
        via the executable in order to save time to not have to restart the
        network many times.
        Make sure the network definition folder argument in the test and in the
        execution are the same, e.g.:

        $ lnregtestnet --nodedata_folder /path/to/lnregtestnet/test/test_data
        """
        testnet = Network(
            network_definition_location='star_ring',
            nodedata_folder=test_data_dir,
            from_scratch=True, node_limit='Z')
        testnet.run_from_background()
        # do tests
        testnet.master_node_print_networkinfo()
        testnet.master_node_graph_view()
