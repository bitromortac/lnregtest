import asyncio
import os
import unittest
import time

from lnregtest.lib.network import Network
from lnregtest.lib.utils import format_dict, dict_comparison
from lnregtest.lib.common import logger_config

import logging.config
logging.config.dictConfig(logger_config)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.handlers[0].setLevel(logging.INFO)

test_dir = os.path.dirname(os.path.realpath(__file__))
test_data_dir = os.path.join(test_dir, 'test_data')


class TestBasicNetwork(unittest.TestCase):
    def test_restart_network(self):
        """
        Test for creating and restoring a network.

        To be able to restore from a previously created network,
        a nodedata_folder has to be given.
        """

        # create network fixture
        testnet_from_scratch = Network(
            nodedata_folder=test_data_dir,
            network_definition_location='star_ring',
            from_scratch=True, node_limit='C')
        # run_once() just initializes, runs, stores and stops the network
        testnet_from_scratch.run_once()

        # use fixture to start up again
        testnet_loaded = Network(
            nodedata_folder=test_data_dir,
            network_definition_location='star_ring',
            from_scratch=False, node_limit='C')
        testnet_loaded.run_once()

        # Channel ids and node pub keys are random data, therefore a
        # human readable mapping needs to be defined in order those objects
        # to be addressable by developers.
        # These mappings can seen here:
        logger.info("Channel mappings:")
        logger.info(format_dict(testnet_loaded.channel_mapping))
        logger.info("Node mappings:")
        logger.info(format_dict(testnet_loaded.node_mapping))

        # Finally test if the network was restored correctly
        self.assertEqual(
            testnet_from_scratch.channel_mapping,
            testnet_loaded.channel_mapping)

        self.assertEqual(
            testnet_from_scratch.node_mapping,
            testnet_loaded.node_mapping)

    def test_graph_assembly(self):
        """
        Each node has a different view of the network, which is why the
        graph has to be assembled from all the nodes via the listchannels
        command.
        """
        testnet = Network(
            network_definition_location='star_ring', from_scratch=True, node_limit='C')

        graph_fixture = \
            {
                "A": {
                    "1": {
                        "remote_name": "C",
                        "capacity": 5000000,
                        "local_balance": 4496530,
                        "remote_balance": 500000,
                        "commit_fee": 2810,
                        "initiator": True
                    },
                    "4": {
                        "remote_name": "B",
                        "capacity": 4000000,
                        "local_balance": 400000,
                        "remote_balance": 3596530,
                        "commit_fee": 2810,
                        "initiator": False
                    }
                },
                "B": {
                    "4": {
                        "remote_name": "A",
                        "capacity": 4000000,
                        "local_balance": 3596530,
                        "remote_balance": 400000,
                        "commit_fee": 2810,
                        "initiator": True
                    },
                    "5": {
                        "remote_name": "C",
                        "capacity": 10000000,
                        "local_balance": 5046035,
                        "remote_balance": 4950495,
                        "commit_fee": 2810,
                        "initiator": True
                    }
                },
                "C": {
                    "1": {
                        "remote_name": "A",
                        "capacity": 5000000,
                        "local_balance": 500000,
                        "remote_balance": 4496530,
                        "commit_fee": 2810,
                        "initiator": False
                    },
                    "5": {
                        "remote_name": "B",
                        "capacity": 10000000,
                        "local_balance": 4950495,
                        "remote_balance": 5046035,
                        "commit_fee": 2810,
                        "initiator": False
                    }
                }
            }
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


class TestLNDMasterNode(unittest.TestCase):
    # this is a way to more efficiently test, by using one testnet for several
    # tests by employing run_nocleanup()
    @classmethod
    def setUpClass(cls):
        cls.testnet = Network(
            network_definition_location='star_ring', from_scratch=True, node_limit='H')
        cls.testnet.run_nocleanup()

    @classmethod
    def tearDownClass(cls):
        cls.testnet.cleanup()

    def test_master_view(self):
        chan_infos = self.testnet.master_node_graph_view()
        self.assertEqual(12, len(chan_infos))

    def test_async_channel_open(self):
        """Tests the asyncio rpc api for channel creation."""
        channels_before = self.testnet.master_node.listchannels()
        self.assertEqual(6, len(channels_before))

        # open channel with async method
        partner_pubkey = self.testnet.node_mapping['B']
        coro = self.testnet.master_node._a_openchannel(
            partner_pubkey,
            100000,
            0
        )
        asyncio.run(coro)
        self.testnet.bitcoind.mine_blocks(3)
        self.testnet.master_node.wait_for_log("HTLC manager started", offset=0)

        channels_after = self.testnet.master_node.listchannels()
        self.assertEqual(7, len(channels_after))


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
