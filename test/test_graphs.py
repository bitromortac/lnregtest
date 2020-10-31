"""
Tests for the predefined graphs.
"""
from unittest import TestCase
from lnregtest.lib.graph_testing import graph_test

from lnregtest.network_definitions import (
    star_ring,
    star_ring_electrum,
    default,
    mutated_default
)


class GraphTests(TestCase):
    """
    Tests shapes of several predefined graphs.
    """
    def test_star_ring(self):
        graph_test(star_ring.nodes)

    def test_default(self):
        graph_test(default.nodes)

    def test_mutated_default(self):
        graph_test(mutated_default.nodes)

    def test_star_ring_electrum(self):
        graph_test(star_ring_electrum.nodes)
