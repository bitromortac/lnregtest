#!/bin/bash
python3 -m pip install --upgrade pip

# electrum
rm -rf electrum
git clone https://github.com/spesmilo/electrum.git
cd electrum
python3 -m pip install --upgrade .
cd ..
pip install pycryptodomex
pip install pyqt5

# electrumx
rm -rf electrumx
git clone https://github.com/spesmilo/electrumx.git
cd electrumx
python3 -m pip install --upgrade .
