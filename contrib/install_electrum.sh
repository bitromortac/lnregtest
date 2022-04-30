#!/bin/bash
python3 -m pip install --upgrade pip

# electrum
ELECTRUM_REF=${ELECTRUM_REF:-master}
rm -rf electrum
git clone --depth=1 -b ${ELECTRUM_REF} https://github.com/spesmilo/electrum.git
cd electrum
python3 -m pip install --upgrade .
cd ..
pip install pycryptodomex
pip install pyqt5

# electrumx
# electrumx stopped issuing tags in 2020, hence this workaround for shallow clone
ELECTRUMX_REF=${ELECTRUMX_REF:-master}
rm -rf electrumx
mkdir electrumx
cd electrumx
git init -b master
git remote add origin https://github.com/spesmilo/electrumx.git
git fetch --depth=1 origin ${ELECTRUMX_REF}
git reset --hard FETCH_HEAD
python3 -m pip install --upgrade .
