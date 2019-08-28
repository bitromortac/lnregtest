"""
Implements a lightning network topology:
"""
nodes = {
    'A': {
        'grpc_port': 11009,
        'rest_port': 8080,
        'port': 9735,
        'base_fee_msat': 1,
        'fee_rate': 0.000001,
        'channels': {
            1: {
                'to': 'C',
                'capacity': 5000000,
                'ratio_local': 9,
                'ratio_remote': 1,
            },
            2: {
                'to': 'E',
                'capacity': 3000000,
                'ratio_local': 7,
                'ratio_remote': 3,
            },
            3: {
                'to': 'G',
                'capacity': 2500000,
                'ratio_local': 9,
                'ratio_remote': 1,
            },
        }
    },
    'B': {
        'grpc_port': 11010,
        'rest_port': 8081,
        'port': 9736,
        'base_fee_msat': 2,
        'fee_rate': 0.000001,
        'channels': {
            4: {
                'to': 'A',
                'capacity': 4000000,
                'ratio_local': 9,
                'ratio_remote': 1,
            },
            5: {
                'to': 'C',
                'capacity': 10000000,
                'ratio_local': 5.1,
                'ratio_remote': 5,
            },
        }
    },
    'C': {
        'grpc_port': 11011,
        'rest_port': 8082,
        'port': 9737,
        'base_fee_msat': 1,
        'fee_rate': 0.000003,
        'channels': {
            6: {
                'to': 'D',
                'capacity': 10000000,
                'ratio_local': 5.1,
                'ratio_remote': 5,
            },
        }
    },
    'D': {
        'grpc_port': 11012,
        'rest_port': 8083,
        'port': 9738,
        'base_fee_msat': 1,
        'fee_rate': 0.000002,
        'channels': {
            7: {
                'to': 'A',
                'capacity': 6000000,
                'ratio_local': 7,
                'ratio_remote': 3,
            },
            8: {
                'to': 'E',
                'capacity': 10000000,
                'ratio_local': 5.1,
                'ratio_remote': 5,
            },
        }
    },
    'E': {
        'grpc_port': 11013,
        'rest_port': 8084,
        'port': 9739,
        'base_fee_msat': 2,
        'fee_rate': 0.000003,
        'channels': {
            9: {
                'to': 'F',
                'capacity': 10000000,
                'ratio_local': 5.1,
                'ratio_remote': 5,
            },
        }
    },
    'F': {
        'grpc_port': 11014,
        'rest_port': 8085,
        'port': 9740,
        'base_fee_msat': 1,
        'fee_rate': 0.000001,
        'channels': {
            10: {
                'to': 'G',
                'capacity': 10000000,
                'ratio_local': 5.1,
                'ratio_remote': 5,
            },
            11: {
                'to': 'A',
                'capacity': 7000000,
                'ratio_local': 9,
                'ratio_remote': 1,
            },
        }
    },
    'G': {
        'grpc_port': 11015,
        'rest_port': 8086,
        'port': 9741,
        'base_fee_msat': 1,
        'fee_rate': 0.000001,
        'channels': {
            12: {
                'to': 'B',
                'capacity': 10000000,
                'ratio_local': 5.1,
                'ratio_remote': 5,
            },
        }
    }
}
