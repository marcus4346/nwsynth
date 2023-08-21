from pynput.keyboard import Listener
from pynput.keyboard._win32 import Key, KeyCode

from .constants import *
from .sound_generator import SoundGenerator

class KeyboardListener:
    def __init__(self, sg: SoundGenerator):
        self._sg = sg
        self._pressed_keys: set[int] = set()
        self._listener = Listener(self._on_press, self._on_release)

    def _on_press(self, key):
        if key is not None:
            if isinstance(key, KeyCode):
                if key.char == '\x03':
                    # Ctrl-C
                    self._listener.stop()
                    return
                vk = key.vk
            elif isinstance(key, Key):
                vk = key.value.vk
            if vk in OCTAVE_SELECTION_KEYS:
                self._sg.set_octave(vk)
            elif vk in INSTRUMEMT_SELECTION_KEYS:
                self._sg.set_instrument(vk)
            elif vk in TONE_KEYS + PERCUSSION_INSTRUMENT_KEYS and vk not in self._pressed_keys:
                self._sg.key_events.put((vk, KeyStatus.PRESSED))
                self._pressed_keys.add(vk)

    def _on_release(self, key):
        if key is not None:
            if isinstance(key, KeyCode):
                vk = key.vk
            if isinstance(key, Key):
                vk = key.value.vk
            if vk in self._pressed_keys:
                if vk in TONE_KEYS:
                    self._sg.key_events.put((vk, KeyStatus.RELEASED))
                self._pressed_keys.remove(vk)
    
    def listen(self):
        self._listener.start()
        self._listener.join()
