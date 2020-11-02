import os

# define waiting periods
WAIT_AFTER_MINING_THREE = 0.5
WAIT_AFTER_ALL_LND_STARTED = 1
WAIT_AFTER_FILLING_WALLETS = 3
WAIT_BEFORE_CLEANUP = 1
WAIT_SYNC_BITCOIND = 1
WAIT_SYNC_ELECTRUMX = 1

common_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.join(common_path, '../../')

logger_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'file': {
            'format': '[%(asctime)s %(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'standard': {
            'format': '%(message)s',
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',  # Default is stderr
        },
        'file': {
            'level': 'DEBUG',
            'formatter': 'file',
            'class': 'logging.FileHandler',
            'filename': os.path.join(root_path, 'regtestnet.log'),
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['default', 'file'],
            'level': 'DEBUG',
            'propagate': True
        },
    }
}
