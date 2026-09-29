"""
audio_manager.py - Centralized Audio Management System for Eagle-1-64Bit

Provides centralized, robust control over sound effects, music playback, channel management,
voice limiting / anti-clipping, engine thruster audio modulation, volume controls,
mute toggle, and settings persistence.
"""

import os
import json
import time
import pygame

from eagle1.paths import DATA_DIR, audio_search_dirs

# Default Audio Configuration
DEFAULT_SETTINGS = {
    "master_volume": 0.8,
    "sfx_volume": 0.8,
    "music_volume": 0.6,
    "is_muted": False,
}

# Dedicated Mixer Channels (0-15)
# Core channels (0-7): Guaranteed to exist even on default 8-channel mixer
CH_PLAYER_WEAPON_1 = 0
CH_ENEMY_WEAPON = 1
CH_IMPACTS = 2
CH_EXPLOSION_1 = 3
CH_WARNINGS = 4
CH_PICKUPS = 5
CH_UI = 6
CH_ENGINE = 7

# Extended channels (8-15): Dynamically allocated when mixer permits
CH_PLAYER_WEAPON_2 = 8
CH_EXPLOSION_2 = 9
CH_TACTICAL = 10

# Mapping sounds to preferred dedicated channels (or None for general pool)
SOUND_CHANNELS = {
    "laser_player": [CH_PLAYER_WEAPON_1, CH_PLAYER_WEAPON_2],
    "laser_rapid": [CH_PLAYER_WEAPON_1, CH_PLAYER_WEAPON_2],
    "rocket_launch": [CH_PLAYER_WEAPON_1, CH_PLAYER_WEAPON_2],
    "rocket_lock": [CH_PLAYER_WEAPON_1],
    "laser_enemy": [CH_ENEMY_WEAPON],
    "hit": [CH_IMPACTS],
    "explosion": [CH_EXPLOSION_1, CH_EXPLOSION_2],
    "explosion_small": [CH_EXPLOSION_1, CH_EXPLOSION_2],
    "player_damage": [CH_WARNINGS],
    "shield_regen": [CH_PICKUPS],
    "health_pickup": [CH_PICKUPS],
    "powerup_pickup": [CH_PICKUPS],
    "enemy_defeat": [CH_PICKUPS],
    "ui_click": [CH_UI],
    "ui_hover": [CH_UI],
    "airstrike_siren": [CH_TACTICAL],
    "engine_loop": [CH_ENGINE],
}

# Minimum cooldown interval (in ms) to prevent ear-piercing volume stacking / clipping
SOUND_MIN_INTERVALS = {
    "laser_player": 40,
    "laser_rapid": 25,
    "laser_enemy": 50,
    "hit": 35,
    "explosion": 80,
    "explosion_small": 50,
    "ui_click": 40,
    "ui_hover": 60,
    "player_damage": 300,
    "shield_regen": 200,
    "rocket_lock": 150,
}


class AudioManager:
    """Centralized, fault-tolerant Audio Controller."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.enabled = False
        self.base_dir = str(DATA_DIR.parent)
        self.settings_file = os.path.join(str(DATA_DIR), "audio_settings.json")

        self.sfx_dir = ""
        self.music_dir = ""
        for audio_dir in audio_search_dirs():
            sfx_candidate = os.path.join(str(audio_dir), "sfx")
            music_candidate = os.path.join(str(audio_dir), "music")
            if os.path.isdir(sfx_candidate) and os.path.isdir(music_candidate):
                self.sfx_dir = sfx_candidate
                self.music_dir = music_candidate
                break

        if not self.sfx_dir or not self.music_dir:
            primary_audio_dir = str(audio_search_dirs()[0])
            self.sfx_dir = os.path.join(primary_audio_dir, "sfx")
            self.music_dir = os.path.join(primary_audio_dir, "music")

        # Load persisted settings
        self.settings = self._load_settings()

        # Cache for loaded Sound objects
        self.sounds = {}
        self.last_play_time = {}
        self.channel_toggle = {}
        self.current_music = None
        self.engine_playing = False
        self.music_paused = False
        self.engine_channel = None
        self.last_engine_vol = -1.0
        self.last_intense_time = 0.0

        self._init_mixer()

    def _load_settings(self):
        """Loads audio settings from JSON or creates defaults."""
        settings = dict(DEFAULT_SETTINGS)
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    settings.update(loaded)
        except Exception as e:
            print(f"[AudioManager] Warning: Could not load audio settings ({e}), using defaults.")
        return settings

    def save_settings(self):
        """Persists current audio settings to disk."""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"[AudioManager] Warning: Could not save audio settings ({e})")

    def _init_mixer(self):
        """Safely initializes pygame.mixer with low latency settings."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 1024)
                pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            self.enabled = True
        except Exception as e:
            print(f"[AudioManager] Audio device init failed: {e}. Running in silent mode.")
            self.enabled = False
            return

        # Ensure audio files exist; generate if missing
        self._ensure_audio_files()

        # Preload sound effects
        self._preload_sounds()

        # Update initial volumes
        self._apply_volumes()

    def _ensure_audio_files(self):
        """Generates audio files if they are not found in the project."""
        test_file = os.path.join(self.sfx_dir, "laser_player.wav")
        if not os.path.exists(test_file):
            print("[AudioManager] Audio assets not found. Generating default sound suite...")
            try:
                from tools import generate_audio_assets
                generate_audio_assets.generate_all()
            except Exception as e:
                print(f"[AudioManager] Error auto-generating audio assets: {e}")

    def _preload_sounds(self):
        """Preloads all SFX into memory."""
        if not self.enabled or not os.path.exists(self.sfx_dir):
            return

        for fname in os.listdir(self.sfx_dir):
            if fname.lower().endswith((".wav", ".ogg", ".mp3")):
                name = os.path.splitext(fname)[0]
                full_path = os.path.join(self.sfx_dir, fname)
                try:
                    snd = pygame.mixer.Sound(full_path)
                    self.sounds[name] = snd
                except Exception as e:
                    print(f"[AudioManager] Warning: Could not load sound {fname}: {e}")

    def _apply_volumes(self):
        """Applies current master, music, and SFX volumes to mixer."""
        if not self.enabled:
            return

        master = self.settings["master_volume"]
        sfx = self.settings["sfx_volume"]
        music = self.settings["music_volume"]
        is_muted = self.settings["is_muted"]

        effective_sfx = 0.0 if is_muted else (master * sfx)
        effective_music = 0.0 if is_muted else (master * music)

        # Update loaded SFX volumes
        for name, snd in self.sounds.items():
            if name == "engine_loop":
                continue  # Engine volume is dynamically modulated
            snd.set_volume(effective_sfx)

        # Update music playback volume
        try:
            pygame.mixer.music.set_volume(effective_music)
        except Exception:
            pass

    # -------------------------------------------------------------
    # Volume & Mute Controls
    # -------------------------------------------------------------
    def get_master_volume(self):
        return self.settings["master_volume"]

    def set_master_volume(self, val):
        self.settings["master_volume"] = max(0.0, min(1.0, float(val)))
        self._apply_volumes()
        self.save_settings()

    def get_sfx_volume(self):
        return self.settings["sfx_volume"]

    def set_sfx_volume(self, val):
        self.settings["sfx_volume"] = max(0.0, min(1.0, float(val)))
        self._apply_volumes()
        self.save_settings()

    def get_music_volume(self):
        return self.settings["music_volume"]

    def set_music_volume(self, val):
        self.settings["music_volume"] = max(0.0, min(1.0, float(val)))
        self._apply_volumes()
        self.save_settings()

    def is_muted(self):
        return self.settings["is_muted"]

    def toggle_mute(self):
        self.settings["is_muted"] = not self.settings["is_muted"]
        self._apply_volumes()
        self.save_settings()
        return self.settings["is_muted"]

    def set_mute(self, muted):
        self.settings["is_muted"] = bool(muted)
        self._apply_volumes()
        self.save_settings()

    # -------------------------------------------------------------
    # Channel Helper
    # -------------------------------------------------------------
    def _get_channel(self, ch_id):
        """
        Safely retrieves a pygame.mixer.Channel object.
        Dynamically expands mixer channel capacity if ch_id >= get_num_channels().
        Falls back to pygame.mixer.find_channel() or None on failure, guaranteeing no IndexError or crash.
        """
        if not self.enabled:
            return None
        try:
            if not pygame.mixer.get_init():
                return None

            num_channels = pygame.mixer.get_num_channels()
            if ch_id >= num_channels:
                try:
                    pygame.mixer.set_num_channels(max(16, ch_id + 1))
                    num_channels = pygame.mixer.get_num_channels()
                except Exception:
                    pass

            if ch_id < num_channels:
                return pygame.mixer.Channel(ch_id)
            else:
                return pygame.mixer.find_channel()
        except Exception:
            try:
                return pygame.mixer.find_channel()
            except Exception:
                return None

    # -------------------------------------------------------------
    # Sound Effect Playback
    # -------------------------------------------------------------
    def play_sfx(self, name, volume_scale=1.0, custom_channel=None):
        """
        Plays a sound effect with anti-clipping cooldown and dedicated channel assignment.
        """
        if not self.enabled or self.settings["is_muted"]:
            return

        snd = self.sounds.get(name)
        if not snd:
            return

        now = int(time.time() * 1000)
        min_interval = SOUND_MIN_INTERVALS.get(name, 30)
        last_time = self.last_play_time.get(name, 0)
        if now - last_time < min_interval:
            return  # Drop voice to prevent clipping/distortion
        self.last_play_time[name] = now

        effective_vol = self.settings["master_volume"] * self.settings["sfx_volume"] * volume_scale
        if effective_vol <= 0.001:
            return

        # Determine target channel
        channel_id = None
        if custom_channel is not None:
            channel_id = custom_channel
        elif name in SOUND_CHANNELS:
            ch_list = SOUND_CHANNELS[name]
            if len(ch_list) == 1:
                channel_id = ch_list[0]
            else:
                # Alternate between assigned channels (e.g. for rapid firing)
                curr_idx = self.channel_toggle.get(name, 0)
                channel_id = ch_list[curr_idx % len(ch_list)]
                self.channel_toggle[name] = curr_idx + 1

        try:
            ch = None
            if channel_id is not None:
                ch = self._get_channel(channel_id)

            if ch is not None:
                ch.set_volume(effective_vol)
                ch.play(snd)
            else:
                # Find any available channel
                snd.set_volume(effective_vol)
                snd.play()
        except Exception:
            pass

    # -------------------------------------------------------------
    # Continuous Engine / Thruster Sound
    # -------------------------------------------------------------
    def update_engine_sound(self, speed_ratio, is_active=True):
        """
        Dynamically modulates engine thruster sound volume based on player speed.
        speed_ratio: 0.0 (stopped/min speed) to 1.0 (max speed).
        """
        if not self.enabled or "engine_loop" not in self.sounds:
            return

        if self.engine_channel is None:
            self.engine_channel = self._get_channel(CH_ENGINE)
        engine_ch = self.engine_channel
        if engine_ch is None:
            return

        if self.settings["is_muted"] or not is_active:
            if self.engine_playing:
                try:
                    engine_ch.stop()
                except Exception:
                    pass
                self.engine_playing = False
            return

        if not self.engine_playing:
            engine_snd = self.sounds["engine_loop"]
            try:
                engine_ch.play(engine_snd, loops=-1)
                self.engine_playing = True
            except Exception:
                return

        # Base idle hum (0.15) to max thrust (0.55)
        raw_vol = 0.15 + 0.40 * max(0.0, min(1.0, speed_ratio))
        effective_vol = self.settings["master_volume"] * self.settings["sfx_volume"] * raw_vol
        if abs(effective_vol - self.last_engine_vol) > 0.005:
            try:
                engine_ch.set_volume(effective_vol)
                self.last_engine_vol = effective_vol
            except Exception:
                pass

    def stop_engine_sound(self):
        """Stops continuous engine loop."""
        if not self.enabled:
            return
        try:
            if self.engine_channel is None:
                self.engine_channel = self._get_channel(CH_ENGINE)
            if self.engine_channel is not None:
                self.engine_channel.stop()
            self.engine_playing = False
        except Exception:
            pass

    # -------------------------------------------------------------
    # Background Music Management
    # -------------------------------------------------------------
    def play_music(self, track_name, loop=True, fade_ms=400):
        """Loads and plays a background music track without blocking delays."""
        if not self.enabled:
            return

        if self.current_music == track_name and pygame.mixer.music.get_busy():
            return

        filename = f"{track_name}.wav"
        full_path = os.path.join(self.music_dir, filename)
        if not os.path.exists(full_path):
            # Try ogg or mp3 fallback
            for ext in [".ogg", ".mp3"]:
                alt_path = os.path.join(self.music_dir, f"{track_name}{ext}")
                if os.path.exists(alt_path):
                    full_path = alt_path
                    break
            else:
                return

        try:
            # Directly load new music stream into SDL_mixer; play with smooth fade_ms
            pygame.mixer.music.load(full_path)
            self.current_music = track_name
            effective_music = 0.0 if self.settings["is_muted"] else (self.settings["master_volume"] * self.settings["music_volume"])
            pygame.mixer.music.set_volume(effective_music)
            loops = -1 if loop else 0
            pygame.mixer.music.play(loops, fade_ms=fade_ms)
            self.music_paused = False
        except Exception as e:
            print(f"[AudioManager] Warning: Could not play music {track_name}: {e}")

    def update_dynamic_music(self, threat_level):
        """
        Dynamically adapts gameplay music based on combat intensity.
        Includes cooldown hysteresis to prevent rapid threshold thrashing.
        threat_level: "normal" or "intense"
        """
        now = time.time()
        if threat_level == "intense":
            self.last_intense_time = now
            target_track = "gameplay_intense"
        else:
            # Maintain intense track for at least 4.0 seconds after threat subsides
            if (now - self.last_intense_time) < 4.0 and self.current_music == "gameplay_intense":
                target_track = "gameplay_intense"
            else:
                target_track = "gameplay_normal"

        if self.current_music != target_track:
            self.play_music(target_track, loop=True, fade_ms=600)

    def stop_music(self, fade_ms=500):
        if not self.enabled:
            return
        try:
            pygame.mixer.music.fadeout(fade_ms)
            self.current_music = None
        except Exception:
            pass

    def pause_music(self):
        if not self.enabled or self.music_paused:
            return
        try:
            pygame.mixer.music.pause()
            self.music_paused = True
        except Exception:
            pass

    def unpause_music(self):
        if not self.enabled or not self.music_paused:
            return
        try:
            pygame.mixer.music.unpause()
            self.music_paused = False
        except Exception:
            pass


def get_audio_manager():
    """Convenience accessor for global AudioManager instance."""
    return AudioManager.get_instance()
