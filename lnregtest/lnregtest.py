from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import logging.config

from lnregtest.lib.network import Network
from lnregtest.lib.common import logger_config
from lnregtest import __version__

logging.config.dictConfig(logger_config)


def main():
    opts = parse_args()

    testnet = Network(
        from_scratch=opts.from_scratch,
        node_limit=opts.node_limit,
        network_definition_location=opts.network_definition,
        nodedata_folder=opts.nodedata_folder
    )
    testnet.run_continuously()


def parse_args():
    parser = ArgumentParser(
        description='lnregtest',
        formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--from_scratch',
        action='store_true',
        help='If True, the network is generated from scratch.',
        default=True)
    parser.add_argument(
        '--node_limit',
        type=str,
        default='Z',
        help="Limits the number of nodes taken from the network definition, "
             "e.g. if you supply 'C', then nodes A, B, and C are created.")
    parser.add_argument(
        '--network_definition',
        type=str,
        default='star_ring',
        help='Defines the network (either absolute path or module name), '
             'examples can be found in lnregtest/network_definitions')
    parser.add_argument(
        '--nodedata_folder',
        type=str,
        default='',
        help='If nothing is specified, a temporary folder is created to store '
             'the runtime data. Otherwise, if an absolute path is given, '
             'the runtime data is stored there and can be restarted.')
    parser.add_argument(
        '--version',
        '-v',
        action='version',
        version="%(prog)s " + __version__)

    return parser.parse_args()
