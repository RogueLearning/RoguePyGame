import math
import struct
import random
import pygame

from UI.colors import Color


class SoundManager:
    def __init__(self):
        self.enabled = False
        try:
            # Initialize mixer with retro-friendly settings
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.enabled = True
        except Exception as e:
            print(f"Sound Manager: could not initialize mixer ({e}). Sound is disabled.")
            
        self._sounds = {}
        if self.enabled:
            self._init_sounds()

    def _init_sounds(self):
        try:
            # 1. Walk / Step Sound (short low pitch bump/thud)
            def walk_freq(t):
                return 150 - t * 400
            self._sounds["walk"] = self._synthesize(walk_freq, duration=0.06, volume=0.08, wave_type="sine")

            # 2. Hit / Melee attack Sound (retro noise/crunch impact)
            def hit_freq(t):
                return 800 - t * 1500
            self._sounds["hit"] = self._synthesize(hit_freq, duration=0.12, volume=0.18, wave_type="noise")

            # 3. Ranged lightning zap Sound (high pitch electric crackle)
            def zap_freq(t):
                return 1800 - t * 4000
            self._sounds["zap"] = self._synthesize(zap_freq, duration=0.25, volume=0.12, wave_type="square")

            # 4. Item pickup Sound (retro arpeggio up)
            def pickup_freq(t):
                if t < 0.04:
                    return 440
                elif t < 0.08:
                    return 554
                elif t < 0.12:
                    return 659
                else:
                    return 880
            self._sounds["pickup"] = self._synthesize(pickup_freq, duration=0.16, volume=0.15, wave_type="sine")

            # 5. Potion drink Sound (bubbling/glug arpeggio)
            def potion_freq(t):
                cycle = int(t * 30) % 3
                return 300 + cycle * 150 + t * 400
            self._sounds["potion"] = self._synthesize(potion_freq, duration=0.3, volume=0.15, wave_type="sine")

            # 6. Stairs / Descend Sound (deep retro drop)
            def stairs_freq(t):
                return 400 - t * 1000
            self._sounds["stairs"] = self._synthesize(stairs_freq, duration=0.4, volume=0.15, wave_type="triangle")

            # 7. Level up / Blessing Sound (triumphant chime)
            def bless_freq(t):
                if t < 0.1:
                    return 523
                elif t < 0.2:
                    return 659
                elif t < 0.3:
                    return 784
                elif t < 0.4:
                    return 1046
                else:
                    return 1318
            self._sounds["bless"] = self._synthesize(bless_freq, duration=0.5, volume=0.15, wave_type="triangle")

            # 8. Chest unlock/open Sound (creaky wooden pitch slide up)
            def chest_freq(t):
                return 200 + t * 600
            self._sounds["chest"] = self._synthesize(chest_freq, duration=0.2, volume=0.15, wave_type="triangle")

            # 9. Mimic reveal/scream (scary screech)
            def mimic_freq(t):
                vibrato = math.sin(t * 100) * 100
                return 800 + vibrato - t * 1200
            self._sounds["mimic"] = self._synthesize(mimic_freq, duration=0.45, volume=0.22, wave_type="square")

            # 10. Game over / Death Sound (sad descending retro chirp)
            def death_freq(t):
                if t < 0.15:
                    return 300 - t * 400
                elif t < 0.35:
                    return 200 - t * 300
                else:
                    return 100 - t * 200
            self._sounds["death"] = self._synthesize(death_freq, duration=0.6, volume=0.2, wave_type="sine")

            # 11. Bow shoot Sound (triangle wave release twang)
            def shoot_freq(t):
                return 400 + math.sin(t * 120) * 100 - t * 600
            self._sounds["shoot"] = self._synthesize(shoot_freq, duration=0.15, volume=0.12, wave_type="triangle")

        except Exception as e:
            print(f"Sound Manager: failed to synthesize retro sounds ({e}). Disabling audio.")
            self.enabled = False

    def _synthesize(self, freq_func, duration, volume, wave_type) -> pygame.mixer.Sound:
        sample_rate = 22050
        num_samples = int(sample_rate * duration)
        samples = bytearray()
        
        phase = 0.0
        for i in range(num_samples):
            t = i / sample_rate
            freq = freq_func(t)
            freq = max(1.0, freq)
            phase += 2.0 * math.pi * freq / sample_rate
            
            if wave_type == "sine":
                val = math.sin(phase)
            elif wave_type == "square":
                val = 1.0 if math.sin(phase) >= 0.0 else -1.0
            elif wave_type == "triangle":
                val = 2.0 * abs((phase / math.pi) % 2.0 - 1.0) - 1.0
            elif wave_type == "noise":
                val = random.uniform(-1.0, 1.0)
            else:
                val = math.sin(phase)
                
            fade_out = 1.0
            if t > duration - 0.02:
                fade_out = max(0.0, (duration - t) / 0.02)
            val *= fade_out * volume
            
            sample = int(val * 32767)
            sample = max(-32768, min(32767, sample))
            samples.extend(struct.pack("<h", sample))
            
        return pygame.mixer.Sound(buffer=samples)

    def play(self, name: str):
        if not self.enabled:
            return
        sound = self._sounds.get(name)
        if sound:
            try:
                sound.play()
            except Exception:
                pass
