from math import pi, sin
from pathlib import Path

from .utils import linear_adsr

class Waveform16:
    def __init__(self, amplitude: int = 8192, sample_length: int = 64):
        assert 0 < amplitude < 32768
        assert sample_length > 0
        self.amplitude = amplitude
        self.sample_length = sample_length
    
    def get_square_wave(self, duty_cycle: float):
        assert 0 < duty_cycle < 1
        wave = []
        for i in range(self.sample_length):
            if i < self.sample_length * duty_cycle:
                wave.append(self.amplitude)
            else:
                wave.append(-self.amplitude)
        return wave

    def get_triangle_wave(self):
        wave = []
        quarter_length = self.sample_length // 4
        for i in range(self.sample_length):
            if i < self.sample_length / 4:
                wave.append(self.amplitude * i // quarter_length)
            elif i < self.sample_length * 3 / 4:
                wave.append(self.amplitude * (self.sample_length // 2 - i) // quarter_length)
            else:
                wave.append(self.amplitude * (i - self.sample_length) // quarter_length)
        return wave

    def get_sawtooth_wave(self):
        wave = []
        half_length = self.sample_length // 2
        for i in range(self.sample_length):
            wave.append(self.amplitude * (half_length - i) // half_length)
        return wave

    def get_sine_wave(self):
        half_length = self.sample_length // 2
        return [int(self.amplitude * sin(i * pi / half_length)) for i in range(self.sample_length)]
    
    def noise_sample(self, short_period=False):
        # On power-up, the shift register is loaded with the value 1.
        lfsr = 1
        wave = []
        while True:
            bit0 = bool(lfsr & 1)
            # Current sample frame
            wave.append(self.amplitude if bit0 else -self.amplitude)
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
            if value:
                frame += 5
            else:
                frame -= 5
            sample.append(frame * 256)
    return sample

_wf16 = Waveform16()
sq1 = _wf16.get_square_wave(1 / 8)
sq2 = _wf16.get_square_wave(2 / 8)
sq3 = _wf16.get_square_wave(3 / 8)
sq4 = _wf16.get_square_wave(4 / 8)
tr = _wf16.get_triangle_wave()
sa = _wf16.get_sawtooth_wave()
si = _wf16.get_sine_wave()
volume_function = linear_adsr((1, 0, 24, 0.25, 5))
