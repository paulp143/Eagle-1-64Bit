"""
generate_audio_assets.py - Procedural High-Fidelity Audio Asset Generator for Eagle-1-64Bit

Generates all required sound effects (SFX) and background music tracks using
NumPy and standard Python wave libraries. Produces clean 44.1kHz 16-bit stereo WAV files.
"""

import os
import wave
import numpy as np

SAMPLE_RATE = 44100


def save_wav(filepath, signal, sample_rate=SAMPLE_RATE):
    """Saves a NumPy 1D (mono) or 2D (stereo, shape [N, 2]) float array (-1.0 to 1.0) as 16-bit WAV."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Normalize to prevent any clipping distortion
    max_val = np.max(np.abs(signal))
    if max_val > 0.98:
        signal = signal * (0.95 / max_val)

    if signal.ndim == 1:
        # Mono -> Stereo
        stereo = np.column_stack((signal, signal))
    else:
        stereo = signal

    int_samples = (stereo * 32767.0).clip(-32767, 32767).astype(np.int16)

    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int_samples.tobytes())


def generate_sfx(output_dir):
    """Generates all sci-fi sound effects."""
    print("Synthesizing Sound Effects...")

    # 1. Player Laser
    dur = 0.14
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    freq = np.geomspace(1100, 220, len(t))
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    carrier = 0.7 * np.sin(phase) + 0.3 * np.sin(phase * 2)
    punch = np.sin(2 * np.pi * 75 * t) * np.exp(-t * 35)
    env = np.exp(-t * 22)
    laser_player = (carrier * 0.75 + punch * 0.25) * env
    save_wav(os.path.join(output_dir, "laser_player.wav"), laser_player)

    # 2. Rapid Laser
    dur = 0.08
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    freq = np.geomspace(1450, 450, len(t))
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    env = np.exp(-t * 35)
    laser_rapid = (0.8 * np.sin(phase) + 0.2 * np.sign(np.sin(phase))) * env
    save_wav(os.path.join(output_dir, "laser_rapid.wav"), laser_rapid)

    # 3. Enemy Laser (lower, menacing buzz)
    dur = 0.18
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    freq = np.geomspace(480, 110, len(t))
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    carrier = 0.6 * np.sin(phase) + 0.4 * np.sign(np.sin(phase))  # Overdriven square edge
    env = np.exp(-t * 16)
    laser_enemy = carrier * env * 0.85
    save_wav(os.path.join(output_dir, "laser_enemy.wav"), laser_enemy)

    # 4. Rocket Launch
    dur = 0.45
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    pop = np.sin(2 * np.pi * 90 * t) * np.exp(-t * 20)
    noise = np.random.uniform(-1.0, 1.0, len(t))
    # Soft low-pass on noise via moving average
    kernel = np.ones(25) / 25
    filtered_noise = np.convolve(noise, kernel, mode='same')
    whoosh_env = (1.0 - np.exp(-t * 40)) * np.exp(-t * 5.5)
    rocket = (pop * 0.5 + filtered_noise * 0.75) * whoosh_env
    save_wav(os.path.join(output_dir, "rocket_launch.wav"), rocket)

    # 5. Rocket Lock-On / Radar Chirp
    dur = 0.16
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    tone1 = np.sin(2 * np.pi * 1760 * t[:len(t)//2]) * np.exp(-t[:len(t)//2] * 25)
    tone2 = np.sin(2 * np.pi * 2349 * t[len(t)//2:]) * np.exp(-t[:len(t)-len(t)//2] * 25)
    lock_chirp = np.concatenate([tone1, tone2]) * 0.5
    save_wav(os.path.join(output_dir, "rocket_lock.wav"), lock_chirp)

    # 6. Hit / Impact
    dur = 0.12
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    thud = np.sin(2 * np.pi * 140 * t) * np.exp(-t * 30)
    noise = np.random.uniform(-1.0, 1.0, len(t)) * np.exp(-t * 45)
    hit = (thud * 0.6 + noise * 0.4)
    save_wav(os.path.join(output_dir, "hit.wav"), hit)

    # 7. Explosion (Heavy blast)
    dur = 0.65
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    sub = np.sin(2 * np.pi * np.geomspace(120, 28, len(t)) * t) * np.exp(-t * 5.0)
    noise = np.random.uniform(-1.0, 1.0, len(t))
    k = np.ones(35) / 35
    f_noise = np.convolve(noise, k, mode='same') * np.exp(-t * 6.5)
    explosion = (sub * 0.55 + f_noise * 0.65)
    save_wav(os.path.join(output_dir, "explosion.wav"), explosion)

    # 8. Small Explosion
    dur = 0.32
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    sub = np.sin(2 * np.pi * np.geomspace(180, 50, len(t)) * t) * np.exp(-t * 12.0)
    noise = np.random.uniform(-1.0, 1.0, len(t))
    k = np.ones(15) / 15
    f_noise = np.convolve(noise, k, mode='same') * np.exp(-t * 14.0)
    explosion_sm = (sub * 0.45 + f_noise * 0.55)
    save_wav(os.path.join(output_dir, "explosion_small.wav"), explosion_sm)

    # 9. Shield Regeneration (shimmering arpeggio)
    dur = 0.35
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    notes = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
    part_len = len(t) // len(notes)
    parts = []
    for i, f in enumerate(notes):
        sub_t = t[:part_len]
        p = 0.4 * np.sin(2 * np.pi * f * sub_t) + 0.15 * np.sin(2 * np.pi * f * 2 * sub_t)
        p *= np.sin(np.pi * sub_t / sub_t[-1])  # smooth bell envelope
        parts.append(p)
    shield_regen = np.concatenate(parts) * 0.6
    save_wav(os.path.join(output_dir, "shield_regen.wav"), shield_regen)

    # 10. Player Damage Alarm (urgent cockpit warning)
    dur = 0.26
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    part_len = len(t) // 2
    sub_t = t[:part_len]
    b1 = np.sin(2 * np.pi * 880 * sub_t) * (0.8 + 0.2 * np.sign(np.sin(2 * np.pi * 880 * sub_t)))
    b2 = np.sin(2 * np.pi * 659.25 * sub_t) * (0.8 + 0.2 * np.sign(np.sin(2 * np.pi * 659.25 * sub_t)))
    env_sub = np.sin(np.pi * sub_t / sub_t[-1])
    alarm = np.concatenate([b1 * env_sub, b2 * env_sub]) * 0.65
    save_wav(os.path.join(output_dir, "player_damage.wav"), alarm)

    # 11. Enemy Defeat (Victory Chime)
    dur = 0.38
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    chord = (
        0.4 * np.sin(2 * np.pi * 740.0 * t) +   # F#5
        0.35 * np.sin(2 * np.pi * 932.3 * t) +  # A#5
        0.35 * np.sin(2 * np.pi * 1108.7 * t) + # C#6
        0.2 * np.sin(2 * np.pi * 1480.0 * t)    # F#6
    )
    env = np.exp(-t * 7.5)
    defeat_chime = chord * env * 0.7
    save_wav(os.path.join(output_dir, "enemy_defeat.wav"), defeat_chime)

    # 12. Health Pickup
    dur = 0.32
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    notes = [440.0, 554.37, 659.25, 880.0]
    part_len = len(t) // len(notes)
    parts = []
    for f in notes:
        sub_t = t[:part_len]
        tone = (0.5 * np.sin(2 * np.pi * f * sub_t) + 0.2 * np.sin(2 * np.pi * f * 2 * sub_t)) * np.exp(-sub_t * 9.0)
        parts.append(tone)
    health_pickup = np.concatenate(parts) * 0.65
    save_wav(os.path.join(output_dir, "health_pickup.wav"), health_pickup)

    # 13. Power-Up Surge Pickup
    dur = 0.35
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    sweep = np.geomspace(280, 1400, len(t))
    phase = 2 * np.pi * np.cumsum(sweep) / SAMPLE_RATE
    tremolo = 0.5 + 0.5 * np.sin(2 * np.pi * 32 * t)
    env = (1.0 - np.exp(-t * 20)) * np.exp(-t * 4.5)
    powerup = (0.6 * np.sin(phase) + 0.25 * np.sin(phase * 1.5)) * tremolo * env
    save_wav(os.path.join(output_dir, "powerup_pickup.wav"), powerup)

    # 14. UI Click
    dur = 0.04
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    ui_click = np.sin(2 * np.pi * 1200 * t) * np.exp(-t * 120) * 0.6
    save_wav(os.path.join(output_dir, "ui_click.wav"), ui_click)

    # 15. UI Hover
    dur = 0.03
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    ui_hover = np.sin(2 * np.pi * 650 * t) * np.exp(-t * 100) * 0.3
    save_wav(os.path.join(output_dir, "ui_hover.wav"), ui_hover)

    # 16. Airstrike Siren / Tactical Beacon
    dur = 0.55
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    siren_freq = 650.0 + 200.0 * np.sin(2 * np.pi * 4.0 * t)
    phase = 2 * np.pi * np.cumsum(siren_freq) / SAMPLE_RATE
    siren = (0.6 * np.sin(phase) + 0.25 * np.sign(np.sin(phase))) * np.sin(np.pi * t / dur) * 0.6
    save_wav(os.path.join(output_dir, "airstrike_siren.wav"), siren)

    # 17. Engine Thruster Loop (seamless 1.2s loop)
    dur = 1.2
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    # Fundamental and harmonics
    r1 = 0.45 * np.sin(2 * np.pi * 55.0 * t)
    r2 = 0.25 * np.sin(2 * np.pi * 110.0 * t)
    r3 = 0.15 * np.sin(2 * np.pi * 165.0 * t)
    # Filtered jet turbulence
    noise = np.random.uniform(-1.0, 1.0, len(t))
    k = np.ones(50) / 50
    jet_hiss = np.convolve(noise, k, mode='same') * 0.25
    engine = r1 + r2 + r3 + jet_hiss
    # Apply crossfade at loop boundary for zero-click seamless looping
    fade_len = int(SAMPLE_RATE * 0.05)
    fade_in = np.linspace(0, 1, fade_len)
    fade_out = np.linspace(1, 0, fade_len)
    engine[:fade_len] = engine[:fade_len] * fade_in + engine[-fade_len:] * fade_out
    save_wav(os.path.join(output_dir, "engine_loop.wav"), engine * 0.5)

    print("All SFX generated successfully.")


def generate_music(output_dir):
    """Generates complete musical loops for Menu, Gameplay, Boss/Intense, and Game Over."""
    print("Synthesizing Music Tracks...")

    def make_kick(duration=0.18):
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        f = np.geomspace(140, 32, len(t))
        phase = 2 * np.pi * np.cumsum(f) / SAMPLE_RATE
        return np.sin(phase) * np.exp(-t * 22) * 0.8

    def make_snare(duration=0.15):
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        body = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 28) * 0.4
        noise = np.random.uniform(-1.0, 1.0, len(t))
        k = np.ones(8) / 8
        f_noise = np.convolve(noise, k, mode='same') * np.exp(-t * 20) * 0.5
        return (body + f_noise) * 0.7

    def make_hihat(duration=0.06):
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        noise = np.random.uniform(-1.0, 1.0, len(t))
        hp = noise - np.convolve(noise, np.ones(6)/6, mode='same')
        return hp * np.exp(-t * 70) * 0.25

    def synth_note(freq, duration, wave_type="saw", release=0.15):
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        if wave_type == "sine":
            sig = np.sin(2 * np.pi * freq * t)
        elif wave_type == "saw":
            sig = 2.0 * (t * freq - np.floor(0.5 + t * freq))
            k = np.ones(4)/4
            sig = np.convolve(sig, k, mode='same')
        elif wave_type == "square":
            sig = np.sign(np.sin(2 * np.pi * freq * t)) * 0.7
        else:
            sig = np.sin(2 * np.pi * freq * t)

        att_len = int(min(len(t) * 0.1, SAMPLE_RATE * 0.01))
        env = np.ones_like(t)
        if att_len > 0:
            env[:att_len] = np.linspace(0, 1, att_len)
        rel_len = int(min(len(t) * 0.4, SAMPLE_RATE * release))
        if rel_len > 0:
            env[-rel_len:] = np.linspace(1, 0, rel_len)
        return sig * env

    # 1. MENU THEME (Ambient Sci-Fi, 92 BPM, 16 beats ~ 10.43s)
    bpm = 92.0
    beat_dur = 60.0 / bpm
    total_beats = 16.0
    total_dur = total_beats * beat_dur
    total_samples = int(SAMPLE_RATE * total_dur)
    menu_track = np.zeros(total_samples)

    chords = [
        [146.83, 220.0, 261.63],
        [116.54, 233.08, 293.66],
        [174.61, 220.0, 261.63],
        [130.81, 196.0, 261.63],
    ]

    for c_idx, chord in enumerate(chords):
        c_start = int(c_idx * 4.0 * beat_dur * SAMPLE_RATE)
        for freq in chord:
            pad = synth_note(freq, 3.9 * beat_dur, "saw", release=0.6) * 0.12
            detune = synth_note(freq * 1.004, 3.9 * beat_dur, "saw", release=0.6) * 0.1
            pad_stereo = (pad + detune)
            end_idx = min(total_samples, c_start + len(pad_stereo))
            menu_track[c_start:end_idx] += pad_stereo[:end_idx - c_start]

    bass_notes = [73.42, 146.83, 110.0, 146.83, 58.27, 116.54, 87.31, 116.54,
                  87.31, 174.61, 130.81, 174.61, 65.41, 130.81, 98.0, 130.81]
    step_dur = beat_dur
    for b_idx, bf in enumerate(bass_notes):
        b_start = int(b_idx * step_dur * SAMPLE_RATE)
        bnote = synth_note(bf, step_dur * 0.85, "saw", release=0.15) * 0.22
        end_idx = min(total_samples, b_start + len(bnote))
        menu_track[b_start:end_idx] += bnote[:end_idx - b_start]

    lead_notes = [
        (0.0, 587.33), (1.5, 659.25), (2.0, 698.46), (3.0, 587.33),
        (4.0, 466.16), (5.5, 587.33), (6.0, 523.25), (7.0, 466.16),
        (8.0, 698.46), (9.5, 783.99), (10.0, 880.0), (11.0, 698.46),
        (12.0, 523.25), (13.5, 587.33), (14.0, 659.25), (15.0, 440.0)
    ]
    for beat_pos, lfreq in lead_notes:
        l_start = int(beat_pos * beat_dur * SAMPLE_RATE)
        lnote = synth_note(lfreq, beat_dur * 0.8, "sine", release=0.3) * 0.16
        end_idx = min(total_samples, l_start + len(lnote))
        menu_track[l_start:end_idx] += lnote[:end_idx - l_start]

    save_wav(os.path.join(output_dir, "menu_theme.wav"), menu_track * 0.85)

    # 2. GAMEPLAY NORMAL THEME (Driving Synthwave, 126 BPM, 16 beats ~ 7.62s)
    bpm = 126.0
    beat_dur = 60.0 / bpm
    total_beats = 16.0
    total_dur = total_beats * beat_dur
    total_samples = int(SAMPLE_RATE * total_dur)
    game_track = np.zeros(total_samples)

    kick = make_kick(0.16)
    snare = make_snare(0.14)
    hihat = make_hihat(0.05)

    for beat in range(16):
        pos = int(beat * beat_dur * SAMPLE_RATE)
        if beat % 2 == 0:
            end_k = min(total_samples, pos + len(kick))
            game_track[pos:end_k] += kick[:end_k - pos] * 0.65
        else:
            end_s = min(total_samples, pos + len(snare))
            game_track[pos:end_s] += snare[:end_s - pos] * 0.55

        end_h1 = min(total_samples, pos + len(hihat))
        game_track[pos:end_h1] += hihat[:end_h1 - pos] * 0.35
        off_pos = pos + int(0.5 * beat_dur * SAMPLE_RATE)
        end_h2 = min(total_samples, off_pos + len(hihat))
        game_track[off_pos:end_h2] += hihat[:end_h2 - off_pos] * 0.28

    bass_roots = [82.41, 98.0, 110.0, 65.41]
    for bar_idx, root in enumerate(bass_roots):
        for step in range(16):
            step_time = (bar_idx * 4.0 + step * 0.25) * beat_dur
            b_start = int(step_time * SAMPLE_RATE)
            pitch = root if (step % 2 == 0) else root * 2.0
            b_note = synth_note(pitch, 0.22 * beat_dur, "saw", release=0.06) * 0.24
            end_idx = min(total_samples, b_start + len(b_note))
            game_track[b_start:end_idx] += b_note[:end_idx - b_start]

    arp_scale = [329.63, 392.00, 493.88, 587.33, 659.25, 783.99]
    for step in range(32):
        step_time = step * 0.5 * beat_dur
        a_start = int(step_time * SAMPLE_RATE)
        note_freq = arp_scale[step % len(arp_scale)]
        anote = synth_note(note_freq, 0.4 * beat_dur, "square", release=0.1) * 0.13
        end_idx = min(total_samples, a_start + len(anote))
        game_track[a_start:end_idx] += anote[:end_idx - a_start]

    save_wav(os.path.join(output_dir, "gameplay_normal.wav"), game_track * 0.82)

    # 3. GAMEPLAY INTENSE / BOSS THEME (140 BPM, 16 beats ~ 6.86s)
    bpm = 140.0
    beat_dur = 60.0 / bpm
    total_beats = 16.0
    total_dur = total_beats * beat_dur
    total_samples = int(SAMPLE_RATE * total_dur)
    intense_track = np.zeros(total_samples)

    kick_fast = make_kick(0.12)
    snare_loud = make_snare(0.16)
    hihat_fast = make_hihat(0.04)

    for beat in range(16):
        pos = int(beat * beat_dur * SAMPLE_RATE)
        end_k1 = min(total_samples, pos + len(kick_fast))
        intense_track[pos:end_k1] += kick_fast[:end_k1 - pos] * 0.75
        pos_k2 = pos + int(0.75 * beat_dur * SAMPLE_RATE)
        end_k2 = min(total_samples, pos_k2 + len(kick_fast))
        intense_track[pos_k2:end_k2] += kick_fast[:end_k2 - pos_k2] * 0.55

        if beat % 2 == 1:
            end_s = min(total_samples, pos + len(snare_loud))
            intense_track[pos:end_s] += snare_loud[:end_s - pos] * 0.65

        for sixteenth in range(4):
            h_pos = pos + int(sixteenth * 0.25 * beat_dur * SAMPLE_RATE)
            end_h = min(total_samples, h_pos + len(hihat_fast))
            intense_track[h_pos:end_h] += hihat_fast[:end_h - h_pos] * 0.25

    roots = [73.42, 87.31, 98.00, 58.27]
    for bar_idx, r in enumerate(roots):
        for step in range(8):
            step_time = (bar_idx * 4.0 + step * 0.5) * beat_dur
            b_start = int(step_time * SAMPLE_RATE)
            bnote = synth_note(r, 0.42 * beat_dur, "saw", release=0.08) * 0.35
            end_idx = min(total_samples, b_start + len(bnote))
            intense_track[b_start:end_idx] += bnote[:end_idx - b_start]

    threat_notes = [587.33, 622.25, 587.33, 698.46, 783.99, 698.46, 880.0, 830.61]
    for i, t_f in enumerate(threat_notes):
        t_start = int(i * 2.0 * beat_dur * SAMPLE_RATE)
        tnote = synth_note(t_f, 1.8 * beat_dur, "saw", release=0.2) * 0.2
        end_idx = min(total_samples, t_start + len(tnote))
        intense_track[t_start:end_idx] += tnote[:end_idx - t_start]

    save_wav(os.path.join(output_dir, "gameplay_intense.wav"), intense_track * 0.82)

    # 4. GAME OVER THEME (Somber, 72 BPM, 8 beats ~ 6.67s)
    bpm = 72.0
    beat_dur = 60.0 / bpm
    total_beats = 8.0
    total_dur = total_beats * beat_dur
    total_samples = int(SAMPLE_RATE * total_dur)
    gameover_track = np.zeros(total_samples)

    cadence = [
        [146.83, 220.0, 261.63],
        [130.81, 196.0, 246.94],
        [116.54, 174.61, 233.08],
        [110.0, 164.81, 220.0],
    ]
    for idx, chord in enumerate(cadence):
        c_start = int(idx * 2.0 * beat_dur * SAMPLE_RATE)
        for cf in chord:
            pad = synth_note(cf, 1.95 * beat_dur, "saw", release=0.4) * 0.15
            end_idx = min(total_samples, c_start + len(pad))
            gameover_track[c_start:end_idx] += pad[:end_idx - c_start]

    lead_notes = [
        (0.0, 587.33), (1.0, 523.25),
        (2.0, 466.16), (3.0, 440.00),
        (4.0, 392.00), (5.0, 349.23),
        (6.0, 440.00), (7.0, 293.66)
    ]
    for b_pos, lf in lead_notes:
        l_start = int(b_pos * beat_dur * SAMPLE_RATE)
        lnote = synth_note(lf, 0.9 * beat_dur, "sine", release=0.3) * 0.22
        end_idx = min(total_samples, l_start + len(lnote))
        gameover_track[l_start:end_idx] += lnote[:end_idx - l_start]

    save_wav(os.path.join(output_dir, "gameover_theme.wav"), gameover_track * 0.8)

    print("All Music Tracks generated successfully.")


def generate_all(output_root=None):
    if output_root is None:
        # Default to project root audio directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        audio_dir = os.path.join(project_root, "audio")
    else:
        audio_dir = output_root

    sfx_dir = os.path.join(audio_dir, "sfx")
    music_dir = os.path.join(audio_dir, "music")

    generate_sfx(sfx_dir)
    generate_music(music_dir)
    print("Audio assets generation complete!")


if __name__ == "__main__":
    generate_all()
