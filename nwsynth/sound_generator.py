from queue import SimpleQueue
from types import FunctionType

import numpy as np
from numpy import ndarray

from .config import *
from .constants import *
from .mixer import Mixer
from .waveform import *



class Key:
    def __init__(self, instrument: list, freq: float, play_once: bool, volume_adsr: FunctionType):
        self.status = KeyStatus.PRESSED
        self.ticks = 0
        self.ticks_since_released = 0
        self.instrument = np.array(instrument, np.int16)
        self.freq = freq
        self.play_once = play_once
        self.volume = 0
        self.volume_adsr = volume_adsr
        self.playback_place = 0.0

class SoundGenerator:
    @classmethod
    def _get_freq_table(cls, middle_a_freq: float):
        # When middle_a_freq is 440,
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

        # [start] --- [-9 as Middle C] --- [0 as Middle A] --- [stop]
        # and stop - start == len(TONE_KEYS) - 1
        rel_freq_list = np.logspace(
            -9 - MIDDLE_C_INDEX + main_config['middleCOffset'],
            len(TONE_KEYS) - MIDDLE_C_INDEX - 10 + main_config['middleCOffset'],
            num=len(TONE_KEYS),
            base=pow(2, 1 / 12)
        )
        freq_table = {}
        for index, vk in enumerate(TONE_KEYS):
            freq_table[vk] = rel_freq_list[index] * middle_a_freq
        return freq_table

    def __init__(self, mixer: Mixer, middle_a_freq: float = 440):
        self._mixer = mixer
        self._freq_table = self._get_freq_table(middle_a_freq)
        self.key_events: SimpleQueue[int, int] = SimpleQueue()
        self._activated_keys: dict[int, Key] = {}
        self.octave = 4
        self.instrument = instrument_lists[default_instrument]

    def _get_all_items(self, queue: SimpleQueue) -> set[int]:
        set_ = set()
        for _ in range(queue.qsize()):
            set_.add(queue.get())
        return set_
    
    def _get_key(self, vk: int) -> Key:
        if self.instrument['type'] == 'builtin':
            waveform = builtin[self.instrument['name']](*self.instrument['args'])
            freq = self._freq_table[vk] * 2 ** (self.octave - 4)
            play_once = False
        elif self.instrument['type'] == 'custom':
            try:
                key_info = custom_instruments[self.instrument['name']][str(TONE_KEYS.index(vk) - MIDDLE_C_INDEX)]
            except KeyError:
                return
            waveform = custom[key_info['waveform']]
            freq = key_info['freq']
            play_once = key_info['play_once']
        adsr = self.instrument['adsr']
        if adsr['type'] == 'linear':
            volume_function = linear_adsr(adsr['args'])
        else:
            volume_function = lambda *_: 1
        return Key(
            waveform,
            freq,
            play_once,
            volume_function
        )
    
    def _get_percussion_key(self, vk: int) -> Key:
        try:
            key_info = percussion_instrument[PERCUSSION_INSTRUMENT_KEYS.index(vk)]
        except IndexError:
            return
        waveform = custom[key_info['waveform']]
        freq = key_info['freq']
        play_once = key_info['play_once']
        volume_function = lambda *_: 1
        adsr = key_info.get('adsr')
        if adsr:
            if adsr['type'] == 'linear':
                volume_function = linear_adsr(adsr['args'])
        return Key(
            waveform,
            freq,
            play_once,
            volume_function
        )
    
    def _get_wave(self, key: Key, volume: float, freq: float) -> ndarray:
        # 调整音调：将采样（乐器）数组拉长/收缩，以符合目标频率
        new_sample_length = int(SAMPLE_RATE / freq)
        new_sample_indices = np.linspace(0, key.instrument.size, new_sample_length, endpoint=False).astype(int)
        new_sample = key.instrument[new_sample_indices]
        # 生成1帧（1/60秒）的音频流：将调整好的采样 以一个偏移量（上次的采样回放位置），进行如下操作
        sample_offset = int(key.playback_place * new_sample_length)
        tick_sample_indices = np.arange(sample_offset, SAMPLE_COUNT_IN_A_TICK + sample_offset) % new_sample_length
        if key.play_once:
            # 仅将第一次播放的数据放置在1帧音频数组里
            playback_times = np.arange(sample_offset, SAMPLE_COUNT_IN_A_TICK + sample_offset) // new_sample_length
            is_first_playback = np.logical_not(playback_times)
            tick_sample = np.zeros(SAMPLE_COUNT_IN_A_TICK, np.int16)
            tick_sample[is_first_playback] = new_sample[tick_sample_indices][is_first_playback]
            if new_sample_length == SAMPLE_COUNT_IN_A_TICK or not np.all(is_first_playback):
                # 第一次播放完毕，标记为结束
                key.status = KeyStatus.FINISHED
        else:
            # 首尾相连铺满至1帧音频数组里
            tick_sample = new_sample[tick_sample_indices]
        # 保存本次的采样回放位置
        key.playback_place = (tick_sample_indices[-1] + 1) / new_sample_length
        # 应用音量
        wave = np.multiply(tick_sample, volume, casting='unsafe').astype(np.int16)
        return wave

    def _process_key(self, vk: int):
        key = self._activated_keys[vk]
        channel = self._mixer.input_channels[vk]
        status = key.status
        if status != KeyStatus.FINISHED:
            volume = key.volume_adsr(
                key.status,
                key.ticks,
                key.ticks_since_released
            )
            if status == KeyStatus.RELEASED and volume == 0:
                self._activated_keys[vk].status = KeyStatus.FINISHED
            else:
                wave = self._get_wave(key, volume, key.freq)
                key.ticks += 1
                if status == KeyStatus.RELEASED:
                    key.ticks_since_released += 1
                channel.put(wave)
        
    def generate(self):
        while True:
            for _ in range(self.key_events.qsize()):
                vk, event = self.key_events.get()
                if event == KeyStatus.PRESSED:
                    if vk in TONE_KEYS:
                        key = self._get_key(vk)
                    elif vk in PERCUSSION_INSTRUMENT_KEYS:
                        key = self._get_percussion_key(vk)
                    if key is None:
                        continue
                    self._activated_keys[vk] = key
                elif event == KeyStatus.RELEASED:
                    if vk in self._activated_keys:
                        self._activated_keys[vk].status = KeyStatus.RELEASED
            for vk in self._activated_keys:
                self._process_key(vk)
            self._mixer.mix()

    def set_octave(self, vk: int):
        self.octave = vk - OCTAVE_SELECTION_KEYS[0] + 1

    def set_instrument(self, vk: int):
        try:
            self.instrument = instrument_lists[INSTRUMEMT_SELECTION_KEYS.index(vk)]
        except IndexError:
            pass
