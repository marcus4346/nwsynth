from math import pi, sin
from pathlib import Path

from .config import custom_waveforms
from .utils import linear_adsr

class Waveform16:
    def __init__(self, sample_length: int = 64):
        assert sample_length > 0
        self.sample_length = sample_length
    
    def get_square_wave(self, amplitude: int, duty_cycle: float):
        assert 0 < amplitude < 32768
        assert 0 < duty_cycle < 1
        wave = []
        for i in range(self.sample_length):
            if i < self.sample_length * duty_cycle:
                wave.append(amplitude)
            else:
                wave.append(-amplitude)
        return wave

    def get_triangle_wave(self, amplitude: int):
        assert 0 < amplitude < 32768
        wave = []
        quarter_length = self.sample_length // 4
        for i in range(self.sample_length):
            if i < self.sample_length / 4:
                wave.append(amplitude * i // quarter_length)
            elif i < self.sample_length * 3 / 4:
                wave.append(amplitude * (self.sample_length // 2 - i) // quarter_length)
            else:
                wave.append(amplitude * (i - self.sample_length) // quarter_length)
        return wave

    def get_sawtooth_wave(self, amplitude: int):
        assert 0 < amplitude < 32768
        wave = []
        half_length = self.sample_length // 2
        for i in range(self.sample_length):
            wave.append(amplitude * (half_length - i) // half_length)
        return wave

    def get_sine_wave(self, amplitude: int):
        assert 0 < amplitude < 32768
        half_length = self.sample_length // 2
        return [int(amplitude * sin(i * pi / half_length)) for i in range(self.sample_length)]
    
    def get_noise_wave(self, amplitude: int, short_period=False):
        assert 0 < amplitude < 32768
        # On power-up, the shift register is loaded with the value 1.
        lfsr = 1
        wave = []
        while True:
            bit0 = bool(lfsr & 1)
            # Current sample frame
            wave.append(amplitude if bit0 else -amplitude)
            # Feedback is calculated as the exclusive-OR of bit 0 and one other bit:
            # bit 6 if Mode flag is set, otherwise bit 1.
            xor_bit = 6 if short_period else 1
            bit1 = bool(lfsr & 1 << xor_bit)
            feedback_value = bit0 ^ bit1
            # The shift register is shifted right by one bit.
            lfsr >>= 1
            # Bit 14, the leftmost bit, is set to the feedback calculated earlier.
            lfsr |= feedback_value << 14
            if lfsr == 1:
                # 一个周期结束
                break
        return wave
    
def dpcm_loader(path: Path):
    data = path.read_bytes()
    sample = []
    frame = 0
    for byte in data:
        for bit_position in range(8):
            value = byte & 1 << bit_position
            # If the bit is 1, add 2; otherwise, subtract 2.
            # But if adding or subtracting 2 would cause the output level to leave the 0-127 range,
            # （注：此处初始值是0，那么范围为-64 ~ 63）
            # leave the output level unchanged.
            # This means subtract 2 only if the current level is at least 2,（也就是-62）
            # or add 2 only if the current level is at most 125.（也就是61）
            if value:
                if frame <= 61:
                    frame += 2
            else:
                if frame >= -62:
                    frame -= 2
            sample.append(frame * 256)
    return sample

_wf16 = Waveform16()
builtin = {
    'squarewave': _wf16.get_square_wave,
    'trianglewave': _wf16.get_triangle_wave,
    'sawtoothwave': _wf16.get_sawtooth_wave,
    'sinewave': _wf16.get_sine_wave,
    'noisewave': _wf16.get_noise_wave,
}
custom = {}
for name, info in custom_waveforms.items():
    if info['type'] == 'dpcm':
        path = Path(__file__).parent.parent.joinpath('samples').joinpath(info['path'])
        waveform = dpcm_loader(path)
    elif info['type'] == 'builtin':
        waveform = builtin[info['name']](*info['args'])
    custom[name] = waveform
