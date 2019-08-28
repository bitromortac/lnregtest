#!/bin/bash
current_folder=`pwd`
lncli=${current_folder}/../bin/lncli
lnd=${current_folder}/../bin/lnd
bitcoind=${current_folder}/../bin/bitcoind
bitcoincli=${current_folder}/../bin/bitcoin-cli

# clean up folders
killall -9 bitcoind
killall -9 lnd

mkdir bitcoin
mkdir -p lndnodes/A
mkdir -p lndnodes/B
mkdir -p lndnodes/C

# generate configuration files
echo "txindex=1
zmqpubrawblock=tcp://127.0.0.1:28332
zmqpubrawtx=tcp://127.0.0.1:28333
regtest=1
rpcuser=lnd
rpcpassword=123456
" > ./bitcoin/bitcoin.conf

echo "[Application Options]

listen=0.0.0.0:9735
rpclisten=localhost:11009
restlisten=0.0.0.0:8080

[Bitcoin]

bitcoin.active=1
bitcoin.regtest=1
bitcoin.node=bitcoind

[Bitcoind]

bitcoind.rpchost=localhost
bitcoind.rpcuser=lnd
bitcoind.rpcpass=123456
bitcoind.zmqpubrawblock=tcp://127.0.0.1:28332
bitcoind.zmqpubrawtx=tcp://127.0.0.1:28333
" > ./lndnodes/A/lnd.conf

echo "[Application Options]

listen=0.0.0.0:9736
rpclisten=localhost:11010
restlisten=0.0.0.0:8081

[Bitcoin]

bitcoin.active=1
bitcoin.regtest=1
bitcoin.node=bitcoind

[Bitcoind]

bitcoind.rpchost=localhost
bitcoind.rpcuser=lnd
bitcoind.rpcpass=123456
bitcoind.zmqpubrawblock=tcp://127.0.0.1:28332
bitcoind.zmqpubrawtx=tcp://127.0.0.1:28333
" > ./lndnodes/B/lnd.conf

echo "[Application Options]

listen=0.0.0.0:9737
rpclisten=localhost:11011
restlisten=0.0.0.0:8082

[Bitcoin]

bitcoin.active=1
bitcoin.regtest=1
bitcoin.node=bitcoind

[Bitcoind]

bitcoind.rpchost=localhost
bitcoind.rpcuser=lnd
bitcoind.rpcpass=123456
bitcoind.zmqpubrawblock=tcp://127.0.0.1:28332
bitcoind.zmqpubrawtx=tcp://127.0.0.1:28333
" > ./lndnodes/C/lnd.conf

# empty appdata
rm -rf bitcoin/blocks bitcoin/regtest
for node in A B C
do
    cd lndnodes/$node
    rm -rf data  graph  logs  tls.cert  tls.key
    cd ..
    cd ..
done

lna () {
    >&2 echo "lna: $@"
    $lncli --lnddir=./lndnodes/A --rpcserver=127.0.0.1:11009 --macaroonpath=./lndnodes/A/data/chain/bitcoin/regtest/admin.macaroon --network=regtest "$@"
}
lnb () {
    >&2 echo "lnb: $@"
    $lncli --lnddir=./lndnodes/B --rpcserver=127.0.0.1:11010 --macaroonpath=./lndnodes/B/data/chain/bitcoin/regtest/admin.macaroon --network=regtest "$@"
}
lnc () {
    >&2 echo "lnc: $@"
    $lncli --lnddir=./lndnodes/C --rpcserver=127.0.0.1:11011 --macaroonpath=./lndnodes/C/data/chain/bitcoin/regtest/admin.macaroon --network=regtest "$@"
}
mine_blocks () {
    address=`bitcoin-cli getnewaddress`
    $bitcoincli generatetoaddress $@ $address
}
lnd_info() {
    lna getinfo
    lna walletbalance
    lnb getinfo
    lnb walletbalance
    lnc getinfo
    lnc walletbalance
}

# start bitcoind
$bitcoind -datadir=${current_folder}/bitcoin -conf=${current_folder}/bitcoin/bitcoin.conf > bitcoin.log &

# wait a bit for bitcoind to start
sleep 5
# mine some blocks
address=`bitcoin-cli getnewaddress`
mine_blocks 110
$bitcoincli getblockchaininfo
$bitcoincli getbalance

# start lnds
$lnd --lnddir=./lndnodes/A --noseedbackup > lnd_A.log &
$lnd --lnddir=./lndnodes/B --noseedbackup > lnd_B.log &
$lnd --lnddir=./lndnodes/C --noseedbackup > lnd_C.log &

sleep 15

lna getinfo

# determine pubkeys
key_a=$(lna getinfo | jq -r .identity_pubkey)
key_b=$(lnb getinfo | jq -r .identity_pubkey)
key_c=$(lnc getinfo | jq -r .identity_pubkey)

# fill lnd wallets
address_a=$(lna newaddress p2wkh | jq -r .address)
address_b=$(lnb newaddress p2wkh | jq -r .address)
address_c=$(lnc newaddress p2wkh | jq -r .address)

$bitcoincli sendtoaddress $address_a 1
$bitcoincli sendtoaddress $address_b 1
$bitcoincli sendtoaddress $address_c 1

# mine some blocks
mine_blocks 6

# conect and open channel
echo ">>> open channel A->B"
lna connect "${key_b}@localhost:9736"
lna openchannel '--min_confs=0' $key_b 100000
mine_blocks 6
# sleep 5
lnd_info

echo ">>> open channel A->C"
lna connect "${key_c}@localhost:9737"
lna openchannel '--min_confs=0' $key_c 200000
mine_blocks 6
# sleep 5
lnd_info

echo ">>> open channel B->C"
lnb connect "${key_c}@localhost:9737"
lnb openchannel '--min_confs=0' $key_c 300000
mine_blocks 6
# sleep 5
lnd_info

lna listchannels
lnb listchannels
lnc listchannels

while :
do
    sleep 2
done
