from array import array
from math import pow, pi, sin
from pathlib import Path
from threading import Thread
from time import sleep, time
import wave

from pyaudio import PyAudio
from pynput.keyboard import Key, KeyCode, Listener


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


class Instrument:
    sample_rate = 44100

    def __init__(self, sample: list[int], width: int, adsr: tuple[float, int, int, float]) -> None:
        # adsr: (
        #   initial volume,
        #   ticks to get to 100% volume,
        #   ticks to get to sustain volume,
        #   sustain volume
        # )
        assert width in (1, 2)
        self.sample = sample
        self.sample_length = len(sample)
        self.sample_width = width
        self.adsr = adsr

    def generate_wave(self, freq, volume: float) -> bytes:
        wave = array('B')
        wave_length = int(self.sample_rate / freq)
        length_ratio = wave_length / self.sample_length
        for frame_index in range(wave_length):
            frame = int(self.sample[int(frame_index / length_ratio)] * volume)
            if self.sample_width == 1:
                wave.append(frame)
            else:
                wave.extend(frame.to_bytes(2, 'little', signed=True))
        return bytes(wave)
    
class Waveform16:
    def __init__(self, amplitude: int = 8192, sample_length: int = 64) -> None:
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
    

class Main:
    freq_table = {
        # Low G to low B
        'a': 196.00, 'w': 207.65, 's': 220.00, 'e': 233.08, 'd': 246.94,
        # C to E
        'f': 261.63, 't': 277.18, 'g': 293.66, 'y': 311.13, 'h': 329.63,
        # F to A
        'j': 349.23, 'i': 369.99, 'k': 392.00, 'o': 415.30, 'l': 440.00,
        # B flat to high C
        'p': 466.16, ';': 493.88, '\'': 523.25
    }
    freq_table['g'] = 523.25
    freq_table['d'] = 196

    keys = 'awsedftgyhjikolp;\''

    @classmethod
    def _get_freq_table(cls, c_freq: float):
        return {
            key: c_freq * pow(2, (index - 5) / 12) for index, key in enumerate(cls.keys)
        }

    def __init__(self) -> None:
        audio = PyAudio()
        config = audio.get_default_output_device_info()
        self.sample_rate = int(config['defaultSampleRate'])
        self.stream = audio.open(self.sample_rate, 1, 2, output=True)
        self.freq = 0
        self.octave = 4
        self.ticks = 0
        self.waveform = Waveform16(8192, 256).get_square_wave(0.5)
        self.waveform_to_be_set = Waveform16(8192, 256).get_square_wave(0.5)

    def __del__(self) -> None:
        self.stream.close()

    def _get_volume(self, adsr: tuple[float, int, int, float]) -> float:
        if self.ticks < adsr[1]:
            volume = adsr[0] + (1 - adsr[0]) * self.ticks / adsr[1]
        elif self.ticks < adsr[2]:
            volume = 1 - (1 - adsr[3]) * (self.ticks - adsr[1]) / adsr[2]
        else:
            volume = adsr[3]
        return volume

    def stream_forever(self):
        while True:
            if self.freq == 0:
                sleep(1 / 60)
                continue
            instrument = Instrument(self.waveform, 2, (1, 0, 24, 0.05))
            volume = self._get_volume(instrument.adsr)
            data = instrument.generate_wave(self.freq, volume)
            play_times = 0
            while play_times < self.sample_rate / len(data) / 15:
                self.stream.write(data)
                play_times += 1
            self.ticks += 1

    # 监听键盘事件的回调函数asdasd
    def on_press(self, key: KeyCode):
        keychar = getattr(key, 'char', None)
        # freq_table = self._get_freq_table(261.63)
        freq_table = self.freq_table
        if keychar:
            if keychar in freq_table:
                if self.waveform != self.waveform_to_be_set:
                    self.waveform = self.waveform_to_be_set
                self.freq = freq_table[keychar] * 2 ** (self.octave - 5)
                print(self.freq)
                self.ticks = 0
            elif keychar == 'z':
                self.waveform_to_be_set = Waveform16(8192, 256).get_square_wave(0.25)
                print('Set to 0.25')
            elif keychar == 'x':
                self.waveform_to_be_set = Waveform16(8192, 256).get_square_wave(0.375)
                print('Set to 0.375')
            elif keychar == 'c':
                self.waveform_to_be_set = Waveform16(8192, 256).get_square_wave(0.5)
                print('Set to 0.5')
            elif keychar == 'v':
                self.waveform_to_be_set = Waveform16(8192, 256).get_triangle_wave()
                print('Set to triangle')
            elif keychar == 'b':
                self.waveform_to_be_set = Waveform16(8192, 256).get_sawtooth_wave()
                print('Set to sawtooth')
            elif keychar == 'n':
                self.waveform_to_be_set = Waveform16(8192, 256).get_sine_wave()
                print('Set to sine')
            elif ord(keychar) in range(48, 58):
                self.octave = int(keychar)
                print('Set to octave', self.octave)
            elif keychar == '\x03':
                exit()
        elif key == Key.space:
            self.freq = 0
        
    def listen(self):
        # 创建一个监听器并开始监听事件
        with Listener(on_press=self.on_press) as listener:
            listener.join()
main = Main()
Thread(target=main.stream_forever, daemon=True).start()
main.listen()
