from queue import SimpleQueue
from time import sleep
from types import FunctionType

import numpy as np
from numpy import ndarray
from pynput.keyboard import KeyCode

from .constants import *
from .mixer import Mixer
from .utils import Clock, sync_lock
from .waveform import sq4, volume_function


class Key:
    KEY_PRESSED = 1
    KEY_RELEASED = 2
    KEY_FINISHED = 3

    def __init__(self, instrument: list, freq: float, volume_adsr: FunctionType):
        self.status = self.KEY_PRESSED
        self.ticks = 0
        self.ticks_since_released = 0
        self.instrument = np.array(instrument, np.int16)
        self.freq = freq
        self.volume = 0
        self.volume_adsr = volume_adsr
        self.playback_place = 0.0

class SoundGenerator:
    @classmethod
    def _get_freq_table(cls, middle_c_freq: float):
        # When middle_c_freq is 261.63,
        # freq_table is {
        #     # Low G to low B
        #     'a': 196.00, 'w': 207.65, 's': 220.00, 'e': 233.08, 'd': 246.94,
        #     # C to E
        #     'f': 261.63, 't': 277.18, 'g': 293.66, 'y': 311.13, 'h': 329.63,
        #     # F to A
        #     'j': 349.23, 'i': 369.99, 'k': 392.00, 'o': 415.30, 'l': 440.00,
        #     # B flat to high C
        #     'p': 466.16, ';': 493.88, '\'': 523.25
        # }
        # with keys as the corresponding virtual key code
        freq_table = {}
        for index, vk in enumerate(TONE_KEYS):
            freq_table[vk] = middle_c_freq * pow(2, (index - 5) / 12)
        return freq_table

    def __init__(self, mixer: Mixer, middle_c_freq: float = 261.63):
        self._mixer = mixer
        self._freq_table = self._get_freq_table(middle_c_freq)
        self.key_events: SimpleQueue[int, int] = SimpleQueue()
        self._activated_keys: dict[int, Key] = {}
        self.instrument = sq4
        self.octave = 4

    def _get_all_items(self, queue: SimpleQueue) -> set[int]:
        set_ = set()
        for _ in range(queue.qsize()):
            set_.add(queue.get())
        return set_
    
    def _get_wave(self, key: Key, volume: float, freq: float) -> ndarray:
        # 调整音调：将采样（乐器）数组拉长/收缩，以符合目标频率
        new_sample_length = int(SAMPLE_RATE / freq)
        new_sample_indices = np.linspace(0, key.instrument.size, new_sample_length, endpoint=False).astype(int)
        new_sample = key.instrument[new_sample_indices]
        # 生成1帧（1/60秒）的音频流：将调整好的采样 以一个偏移量（上次的采样回放位置） 铺满至1帧音频数组里
        sample_offset = int(key.playback_place * new_sample_length)
        tick_sample_indices = np.arange(sample_offset, SAMPLE_COUNT_IN_A_TICK + sample_offset) % new_sample_length
        tick_sample = new_sample[tick_sample_indices]
        # 保存本次的采样回放位置
        key.playback_place = (tick_sample_indices[-1] + 1) / new_sample_length
        # 应用音量
        wave = np.multiply(tick_sample, volume, casting='unsafe').astype(np.int16)
        return wave

    def _process_key(self, vk: int):
        key = self._activated_keys[vk]
        status = key.status
        if status != Key.KEY_FINISHED:
            volume = key.volume_adsr(
                key.status,
                key.ticks,
                key.ticks_since_released
            )
            if status == Key.KEY_RELEASED and volume == 0:
                self._activated_keys[vk].status = Key.KEY_FINISHED
                return
            channel = self._mixer.input_channels[vk]
            wave = self._get_wave(key, volume, key.freq)
            channel.put(wave)
            key.ticks += 1
            if status == Key.KEY_RELEASED:
                key.ticks_since_released += 1

        
    def generate(self):
        clock = Clock(TICK)
        while True:
            for _ in range(self.key_events.qsize()):
                vk, event = self.key_events.get()
                if event == Key.KEY_PRESSED:
                    key = Key(
                        self.instrument,
                        self._freq_table[vk],
                        volume_function
                    )
                    self._activated_keys[vk] = key
                elif event == Key.KEY_RELEASED:
                    if vk in self._activated_keys:
                        self._activated_keys[vk].status = Key.KEY_RELEASED
            for vk in self._activated_keys:
                self._process_key(vk)
            sync_lock.release()
            clock.sleep()
