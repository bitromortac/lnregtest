lnregtest - Lightning Networks on Bitcoin regtest
=================================================

Implements functioning lightning networks for (Python) integration testing 
operating on a Bitcoin regtest network by running several lightning node 
instances.

The simulated lightning networks can have different shapes as defined
 in the `network_definitions` folder.

An example of a graph (`star_ring`) with 7 nodes and 12 channels is shown 
here (for initial channel balance details, have a look at 
`network_definitions/star_ring.py`):

```
Star-like component with channels (where A is the master node):
A -> B, A -> C, A -> D, A -> E, A -> F, A -> G,
Ring-like component with channels (which surrounds the master node):
B -> C, C -> D, D -> E, E -> F, F -> G, G -> B
```
This star and ring-like lightning network can then be used to test interactions
with the network from the master node's perspective, like rebalancing channels,
routing payments, sending payments and so on.

Features
--------
* No external python dependencies
* Arbitrary lightning network graphs with up to number of nodes on the order of
10 (depends on your resources)
* LND support
* Electrum support
* Lightning graph state comparison
* Restarting from already created networks
* Abstraction of random identifiers (public keys, channel ids) to human readable
  identifiers
* Library and command-line execution
* Automatic sanity check of user defined networks
  
Planned features
----------------
* Arbitrary lightning daemon binary detection (lnd, clightning, ...)
* Time-dependent transaction series

Creating your own network topology
----------------------------------
Networks of arbitrary shape can be defined as a python dictionary in the
`network_definitions` folder. See the examples for a general structure.

The requirements are:
* Node A is the master node
* Nodes are uniquely named by subsequent characters A, B, C, ...
* Channels are uniquely numbered by integers 1, 2, 3, ...
* Ports must be set uniquely

Testing other (python) projects
-----------------------------
Test examples can be found in the `test` folder and more information on how
lnregtest is used for lightning network integration testing can be found in 
[TEST](./test/TEST.md).

This package is also used in production in 
[lndmanage](https://github.com/bitromortac/lndmanage).

Setup
-----
The binaries bitcoind (v0.20.1), bitcoin-cli, lnd (v0.11.1), and lncli are expected to be found in 
`$PATH`, e.g., put these binaries into your ~/bin folder.

You can use the tool in two different standalone modes:

**Git repository mode**:
```
$ git clone https://github.com/bitromortac/lnregtest
$ cd lnregtest
```
Run network:
```
$ python3 lnregtest.py -h
```

**Package mode**:
```
$ python3 -m venv venv
$ source venv/bin/activate
$ python3 -m pip install lnregtest
```
Run network:
```
$ lnregtest -h
```

Test if lnregest works
-------------------------
To run all tests, run `python3 -m unittest discover test` from the root folder.


Troubleshooting
---------------
* `all SubConns are in TransientFailure`:
  Typically, here it happens that lnd is not given enough time to start. **The 
  simulation of a lightning network is memory and CPU intensive.** Each LN
  node needs some time to get up and running and consumes resources.
  Currently, the startup of each lnd node is delayed to distribute CPU load.
  The settings were tested on a quadcore processor and 8 GB of RAM.
* bitcoind and lnd processes are not terminated:
  Sometimes it happens that the processes are not terminated correctly, so
  before you start new tests, make sure to do so manually.

Related Projects
----------------
* Medium article on how regtest lightning networks can be set up: [bitstein-medium](https://medium.com/@bitstein/setting-up-a-bitcoin-lightning-network-test-environment-ab967167594a)
* Dockerized lightning networks: [simverse](https://github.com/darwin/simverse)
* Dockerized version for the medium article: [bitstein-test-env](https://github.com/JeffVandrewJr/bitstein-test-env)
