import os
from datetime import datetime

import yaml


def load_symbols_from_config(config_file, default_symbols : list):
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                symbols = config.get('symbols') if isinstance(config, dict) else None
                if isinstance(symbols, list):
                    return symbols
        except Exception:
            pass
    return list(default_symbols) if default_symbols else []


def save_symbols_to_config(config_file, symbols : list):
    config = {
        'symbols': symbols,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
