lnd_config_template = \
    "[Application Options]\n" \
    "alias={name}\n" \
    "listen=localhost:{lnd_port}\n" \
    "restlisten=localhost:{rest_port}\n" \
    "rpclisten=localhost:{rpc_port}\n" \
    "debuglevel=info\n" \
    "unsafe-disconnect=1\n" \
    "[Bitcoin]\n" \
    "bitcoin.active=1\n" \
    "bitcoin.regtest=1\n" \
    "bitcoin.node=bitcoind\n" \
    "bitcoin.basefee={base_fee_msat}\n" \
    "bitcoin.feerate={fee_rate}\n" \
    "[Bitcoind]\n" \
    "bitcoind.rpchost=localhost\n" \
    "bitcoind.rpcuser=lnd\n" \
    "bitcoind.rpcpass=123456\n" \
    "bitcoind.zmqpubrawblock=tcp://127.0.0.1:28332\n" \
    "bitcoind.zmqpubrawtx=tcp://127.0.0.1:28333"

bitcoind_config_template = \
    "txindex=1\n" \
    "zmqpubrawblock=tcp://127.0.0.1:28332\n" \
    "zmqpubrawtx=tcp://127.0.0.1:28333\n" \
    "regtest=1\n" \
    "rpcuser=lnd\n" \
    "rpcpassword=123456\n" \
    "fallbackfee=0.00001000\n"
