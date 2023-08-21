import json

from pathlib import Path

_config_path = Path(__file__).parent.parent.joinpath('config.json')
with _config_path.open() as f:
    config = json.load(f)
main_config = config['main']
custom_waveforms = config['customWaveforms']
custom_instruments = config['customInstruments']
instrument_lists = config['instrumentLists']
default_instrument = config['defaultInstrument']
percussion_instrument = config['percussionInstrument']
