from configparser import ConfigParser
from pathlib import Path

_config_path = Path(__file__).parent.parent.joinpath('config.ini')
_config = ConfigParser()
_config.read(_config_path)
config = _config['Main']
