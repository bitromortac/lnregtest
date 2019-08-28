#!/bin/bash

# script to clean up data directories

killall -9 bitcoind
killall -9 lnd
git clean -df
