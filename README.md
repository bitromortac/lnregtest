LN regtest network
==================

Implements a lightning network for (python) integration testing based on a 
bitcoin regtest network.

The simulated lightning network's size can have different shapes as defined
 in the `network_definitions` folder.

An example of a graph (`star_ring`) with 7 nodes and 12 channels is shown 
here (for initial channel balance details, have a look at 
`network_definitions/star_ring.py`):

```
Star-like component:
A -> B
A -> C
A -> D
A -> E
A -> F
A -> G
Ring-like component:
B -> C
C -> D
D -> E
E -> F
F -> G
G -> B
```

Features
----------------
* No external python dependencies
* Arbitrary lightning network graphs with a number of nodes ~10 (depends on 
your resources)
* LND support
* Lightning graph state comparison
* Restarting from already created networks
* Abstraction of random identifiers (public keys, channel ids) to human readable
  identifiers
* Library and command-line execution
  
Planned features
----------------
* Arbitrary lightning daemon binary detection (lnd, clightning, ...)
* Time-dependent transaction series

Create your own network topology
---------------------------
Networks of arbitrary shape can be defined as a python dictionary in the
`network_definitions` folder. See the examples for a general structure.

The requirements are:
* Node A is the master node
* Nodes are uniquely named by subsequent characters A, B, C, ...
* Channels are uniquely numbered by incremental integers 1, 2, 3, ...
* Ports must be set uniquely
* Local balances must be larger than remote balances

Testing other (python) projects
-----------------------------
Test examples can be found in the `test` folder and more information on how
lnregtest is used for lightning network integration testing can be found in 
[TEST](./test/TEST.md).

This package is also used in production in 
[lndmanage](https://github.com/bitromortac/lndmanage).

Setup
-----
**In order to have a complete immediate graph view, we need to compile LND
in a special way by setting `defaultTrickleDelay = 1` in `config.go`.**

The binaries bitcoind, bitcoin-cli, lnd, and lncli are expected to be found in 
`$PATH`.

You can use the tool in two different modes:

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
$ virtualenv -p python3 venvs/lnregtest
$ source venvs/lnregtest/bin/activate
$ pip install lnregtest
```
Run network:
```
$ lnregtest -h
```

Test if lnregest works
-------------------------
To run all tests, run
`python3 -m unittest discover test` from the root folder.


Troubleshooting
---------------
* `all SubConns are in TransientFailure`:
  Typically, here it happens that lnd is not given enough time to start. **The 
  simulation of a lightning network is memory and CPU intensive.** Each LN
  node needs some time to get up and running and consumes resources.
  Currently, the startup of each lnd node is delayed to distribute CPU load.
  If you experience startup problems, increase `LOAD_BALANCING_LND_STARTUP_TIME_SEC`
   in `lib.common`. The settings were tested on a quadcore processor and 8 GB of RAM.
* bitcoind and lnd processes are not terminated:
  Sometimes it happens that the processes are not terminated correctly, so
  before you start new tests, make sure to do so manually.
