"""
generate_guitar_chord.py

Ein einfacher Gitarren-Akkord-Generator (Karplus-Strong Plucked String).
Erzeugt WAV-Dateien mit einem kurzen, gezupften Gitarrensound für einfache Akkorde.

Beispiel:
    python generate_guitar_chord.py --chord Gmaj --duration 3.0 --out g_major.wav

"""
import struct
import wave
import math
import random
import argparse
from typing import List

SAMPLE_RATE = 44100

# Frequencies for notes (A4 = 440 Hz). We'll provide a small helper mapping.
NOTE_FREQ = {
    'A4': 440.00,
    'B4': 493.88,
    'C4': 261.63,
    'D4': 293.66,
    'E4': 329.63,
    'F4': 349.23,
    'G4': 392.00,
    'A3': 220.00,
    'B3': 246.94,
    'C3': 130.81,
    'D3': 146.83,
    'E3': 164.81,
    'F3': 174.61,
    'G3': 196.00,
}

CHORDS = {
    'Gmaj': ['G3', 'B3', 'D4'],
    'Cmaj': ['C3', 'E3', 'G3'],
    'Dmaj': ['D3', 'F#3', 'A3'],
    'Em': ['E3', 'G3', 'B3'],
}

# Extend NOTE_FREQ with sharps as needed
NOTE_FREQ['F#3'] = 185.00  # approx


def karplus_strong(frequency: float, duration: float, sample_rate: int = SAMPLE_RATE, decay: float = 0.996) -> List[float]:
    """Generate a plucked-string sound for the given frequency and duration.

    Returns a list of float samples in range [-1.0, 1.0].
    """
    N = int(sample_rate / frequency)
    # Initialize the buffer with noise
    buf = [random.uniform(-1.0, 1.0) for _ in range(N)]
    out = []
    total_samples = int(duration * sample_rate)
    for i in range(total_samples):
        first = buf[i % N]
        second = buf[(i + 1) % N]
        avg = decay * 0.5 * (first + second)
        out.append(avg)
        buf[i % N] = avg
    return out


def mix_signals(signals: List[List[float]]) -> List[float]:
    """Sum multiple signals and normalize to prevent clipping."""
    if not signals:
        return []
    length = max(len(s) for s in signals)
    out = [0.0] * length
    for s in signals:
        for i, v in enumerate(s):
            out[i] += v
    # Normalize
    max_val = max(abs(x) for x in out) or 1.0
    return [x / max_val * 0.9 for x in out]


def write_wav(filename: str, samples: List[float], sample_rate: int = SAMPLE_RATE):
    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        frames = b''.join(struct.pack('<h', int(max(-1.0, min(1.0, s)) * 32767)) for s in samples)
        wf.writeframes(frames)


def chord_to_frequencies(chord_name: str) -> List[float]:
    if chord_name not in CHORDS:
        raise ValueError(f"Unknown chord: {chord_name}")
    freqs = []
    for note in CHORDS[chord_name]:
        if note not in NOTE_FREQ:
            raise ValueError(f"Unknown note: {note}")
        freqs.append(NOTE_FREQ[note])
    return freqs


def generate_chord(chord_name: str, duration: float = 3.0) -> List[float]:
    freqs = chord_to_frequencies(chord_name)
    signals = [karplus_strong(f, duration) for f in freqs]
    return mix_signals(signals)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--chord', default='Gmaj', help='Chord name (e.g. Gmaj, Cmaj, Em)')
    parser.add_argument('--duration', type=float, default=3.0, help='Duration in seconds')
    parser.add_argument('--out', default='chord.wav', help='Output WAV file name')
    args = parser.parse_args()

    samples = generate_chord(args.chord, args.duration)
    write_wav(args.out, samples)
    print(f'WAV written: {args.out} ({len(samples)/SAMPLE_RATE:.2f}s)')
