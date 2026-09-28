"""Small original synthesized sound palette; generated and cached on first run."""
from array import array
from pathlib import Path
import math
import random
import wave


class SoundBank:
    def __init__(self, muted=False):
        self.muted = muted
        self.sounds = {}
        if muted:
            return
        self.load()

    def load(self):
        from ursina import Audio
        directory = Path(__file__).resolve().parent.parent / '.cache' / 'audio'
        directory.mkdir(parents=True, exist_ok=True)
        recipes = {'hit': (.16, 110, .6), 'cast': (.38, 330, .18), 'dodge': (.18, 550, .55),
                   'parry': (.35, 870, .15), 'domain': (1.1, 70, .25),
                   'qte_result': (.5, 660, .08), 'select': (.1, 440, .04), 'round_end': (.8, 220, .1)}
        for name, (duration, frequency, noise) in recipes.items():
            path = directory / f'{name}.wav'
            if not path.exists():
                rng = random.Random(3)
                samples = array('h')
                rate = 22050
                for i in range(int(duration*rate)):
                    t = i/rate
                    env = min(1, t*180)*(1-t/duration)**2
                    sweep = frequency*(1-.32*t/duration)
                    signal = math.sin(math.tau*sweep*t)*.5 + math.sin(math.tau*sweep*1.5*t)*.15 + rng.uniform(-1, 1)*noise
                    samples.append(int(max(-1, min(1, signal*env)) * 14000))
                with wave.open(str(path), 'wb') as audio:
                    audio.setnchannels(1)
                    audio.setsampwidth(2)
                    audio.setframerate(rate)
                    audio.writeframes(samples.tobytes())
            self.sounds[name] = Audio(str(path), autoplay=False, volume=.27)

    def play(self, name):
        if not self.muted and name in self.sounds:
            self.sounds[name].stop()
            self.sounds[name].play()

    def toggle(self):
        self.muted = not self.muted
        if not self.muted and not self.sounds:
            self.load()
        return self.muted
