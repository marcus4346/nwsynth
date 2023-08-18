from threading import Thread

from nwsynth import KeyboardListener, Mixer, SoundGenerator
from nwsynth.constants import MIDDLE_A_FREQ

mixer = Mixer()
sg = SoundGenerator(mixer, MIDDLE_A_FREQ)
kl = KeyboardListener(sg)
Thread(target=mixer.output, daemon=True).start()
Thread(target=mixer.mix, daemon=True).start()
Thread(target=sg.generate, daemon=True).start()
kl.listen()
