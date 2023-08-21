from queue import SimpleQueue
from time import sleep, time

import numpy as np
from numpy import int16, int32
from pyaudio import PyAudio

from .constants import *
from .utils import sync_lock


i16_info = np.iinfo(int16)

class Mixer:
    def __init__(self):
        self.input_channels: dict[int, SimpleQueue[np.ndarray]] = {vk: SimpleQueue() for vk in TONE_KEYS + PERCUSSION_INSTRUMENT_KEYS}
        self._output_channel: SimpleQueue[np.ndarray] = SimpleQueue()
        self._audio = PyAudio()
        self._stream = self._audio.open(
            SAMPLE_RATE,
            1,
            self._audio.get_format_from_width(2),
            output=True
        )

    def __del__(self):
        self._stream.close()
        self._audio.terminate()

    def mix(self):
        while True:
            sync_lock.acquire()
            # Use int32 to prevent overflow on int16 adding
            wave = np.zeros(SAMPLE_COUNT_IN_A_TICK, int32)
            for channel in self.input_channels.values():
                if not channel.empty():
                    channel_wave = channel.get()
                    wave += channel_wave
            # Convert to int16
            wave.clip(i16_info.min, i16_info.max)
            wave = wave.astype(int16)
            self._output_channel.put(wave)

    def output(self):
        while True:
            wave = self._output_channel.get(True)
            print(np.average(wave))
            self._stream.write(wave.tobytes())
            