"""
Module can be used to check if graphs are defined in the correct convention.
"""

from typing import Dict


def graph_test(nodes):
    """
    Tests if a graph was defined in a certain convention.

    :param nodes: nodes definition
    :type nodes: dict
    """
    channel_numbers = sorted(get_channel_numbers(nodes))

    test_node_names_alphabetical(nodes)
    test_channel_numbers_unique(channel_numbers)
    test_ports(nodes)
    test_allowed_node_implementations(nodes)


def test_allowed_node_implementations(nodes: Dict[str, Dict]):
    """
    Tests if the daemon fields in the node definitions is from the
    supported set of daemons.
    """
    allowed_nodes = {None, 'electrum', 'lnd'}  # None is lnd default
    present_nodes = set()
    for n in nodes.values():
        present_nodes.add(n.get('daemon'))
    for pn in present_nodes:
        if pn not in allowed_nodes:
            raise ValueError(
                f"Error in daemon field of graph definition, "
                f"should be one of {allowed_nodes}, is {pn}.")



def get_channel_numbers(nodes):
    """
    Extracts channel numbers from graph definition.

    :param nodes: nodes definintion
    :type nodes: dict
    :return: channel numbers
    :rtype: list(int)
    """
    channels = []
    for node_name, node_data in nodes.items():
        channels.extend(node_data['channels'].keys())
    return channels


def test_node_names_alphabetical(nodes):
    """
    Tests if the names of the nodes were defined in an alpabetical increasing
    order.

    :param nodes: nodes definition
    :type nodes: dict

    :return: True if test matches expectation
    :rtype: bool
    """
    node_names = nodes.keys()
    number_nodes = len(node_names)
    alphabet = [str(chr(i)) for i in range(65, 91)]
    node_names_should = alphabet[:number_nodes]
    assert node_names_should == list(node_names),\
        "Node names do not follow convention A, B, C, ..."


def test_channel_numbers_unique(channel_numbers):
    assert len(set(channel_numbers)) == len(channel_numbers), \
        'Channel numbers are not unique.'


def get_ports(nodes):
    """
    Extracts ports from nodes definition.

    :param nodes: nodes definition
    :type nodes: dict
    :return: lnd ports, grpc ports, rest ports
    :rtype: list, list, list
    """
    ports = []
    grpc_ports = []
    rest_ports = []
    for node_name, node_data in nodes.items():
        ports.append(node_data['port'])
        grpc_ports.append(node_data['grpc_port'])
        rest_ports.append(node_data['port'])
    return ports, grpc_ports, rest_ports


def test_ports(nodes):
    ports, grpc_ports, rest_ports = get_ports(nodes)

    assert len(nodes) == len(ports)
    assert len(nodes) == len(grpc_ports)
    assert len(nodes) == len(rest_ports)

    assert len(ports) == len(set(ports))
    assert len(grpc_ports) == len(set(grpc_ports))
    assert len(rest_ports) == len(set(rest_ports))


if __name__ == '__main__':
    from lnregtest.network_definitions.default import nodes as star_ring_nodes
    graph_test(star_ring_nodes)
