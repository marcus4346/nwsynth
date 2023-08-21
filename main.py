from threading import Thread

from nwsynth import KeyboardListener, Mixer, SoundGenerator

mixer = Mixer()
sg = SoundGenerator(mixer)
kl = KeyboardListener(sg)
Thread(target=sg.generate, daemon=True).start()
kl.listen()
