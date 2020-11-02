nodes = {
    'A': {
        'grpc_port': 11009,
        'rest_port': 8080,
        'port': 9735,
        'base_fee_msat': 1,
        'fee_rate': 0.000001,
        'daemon': 'electrum',
        'channels': {
            1: {
                'to': 'B',
                'capacity': 4000000,
                'ratio_local': 10,
                'ratio_remote': 9,
            },
            2: {
                'to': 'C',
                'capacity': 5000000,
                'ratio_local': 10,
                'ratio_remote': 9,
            },
        }
    },
    'B': {
        'grpc_port': 11010,
        'rest_port': 8081,
        'port': 9736,
        'base_fee_msat': 2,
        'fee_rate': 0.000001,
        'daemon': 'lnd',
        'channels': {
            3: {
                'to': 'C',
                'capacity': 100000,
                'ratio_local': 10,
                'ratio_remote': 0,
            },
        }
    },
    'C': {
        'grpc_port': 11011,
        'rest_port': 8082,
        'port': 9737,
        'base_fee_msat': 1,
        'fee_rate': 0.000003,
        'daemon': 'lnd',
        'channels': {
        }
    },
}
