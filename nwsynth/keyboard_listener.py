from pynput.keyboard import Listener
from pynput.keyboard._win32 import Key, KeyCode

from .constants import INSTRUMEMT_SELECTION_KEYS, OCTAVE_SELECTION_KEYS, TONE_KEYS
from .sound_generator import SoundGenerator

class KeyboardListener:
    KEY_PRESSED = 1
    KEY_RELEASED = 2

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
                self._sg.octave = vk - 48
                return
            if vk in TONE_KEYS and vk not in self._pressed_keys:
                self._sg.key_events.put((vk, self.KEY_PRESSED))
                self._pressed_keys.add(vk)

    def _on_release(self, key):
        if key is not None:
            if isinstance(key, KeyCode):
                vk = key.vk
            if isinstance(key, Key):
                vk = key.value.vk
            if vk in self._pressed_keys:
                self._sg.key_events.put((vk, self.KEY_RELEASED))
                self._pressed_keys.remove(vk)
    
    def listen(self):
        self._listener.start()
        self._listener.join()
