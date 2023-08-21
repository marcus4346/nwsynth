from enum import IntEnum


SAMPLE_RATE = 44100
TICK = 1 / 60
SAMPLE_COUNT_IN_A_TICK = int(SAMPLE_RATE * TICK)  # 735
MIDDLE_A_FREQ = 440  # A440 standard
# [qawsedftgyhjikolp;'], key F is middle C
TONE_KEYS = [ord(char) for char in 'QAWSEDFTGYHJIKOLP'] + [186, 222]
MIDDLE_C_INDEX = 6
# [123456789], key 4 is the default octave
OCTAVE_SELECTION_KEYS = [vk for vk in range(49, 58)]
# [zxcvbnm]
INSTRUMEMT_SELECTION_KEYS = [ord(char) for char in 'ZXCVBNM']
# Numpad 0 to numpad 9
PERCUSSION_INSTRUMENT_KEYS = [vk for vk in range(96, 106)]

class KeyStatus(IntEnum):
    PRESSED = 1
    RELEASED = 2
    FINISHED = 3
