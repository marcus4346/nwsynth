from threading import Thread

from nwsynth import KeyboardListener, Mixer, SoundGenerator

mixer = Mixer()
sg = SoundGenerator(mixer)
kl = KeyboardListener(sg)
Thread(target=mixer.output, daemon=True).start()
Thread(target=mixer.mix, daemon=True).start()
Thread(target=sg.generate, daemon=True).start()
kl.listen()
