Testing
=======

Integration tests reside in the `test` folder.

To run them:
```
$ python3 -m unittest discover test
```

Comparison of network states
----------------------------

The main feature of lnregtest by now is to compare the state
(including balances) of the simulated lightning network before and after
some action.
 
This can be achieved by employing the 
`lnregtest.lib.network.RegtestNetwork.assemble_graph` method, which constructs
the state of the network in form of a python dictionary, by asking all nodes about
their channel status.

These dictionaries can be compared by using `lnregtest.lib.utils.dict_comparison`
(an example for this can be found in
`lnregtest.test.test_basic.TestBasicNetwork.test_graph_assembly`).

Addressing nodes and channels by names and numbers
--------------------------------------------------
The names and channel numbers are defined in `lnregtest.network_definitions.file`.
In a lightning network, there are random identifiers which cannot be known
beforehand like the channel id or the node public key. This is why here we
added a mapping to address channels and nodes. The mappings are found during runtime
in `lnregtest.lib.network.RegtestNetwork.channel_mapping(_inverse)` and 
`lnregtest.lib.network.RegtestNetwork.node_mapping(_inverse)`.
