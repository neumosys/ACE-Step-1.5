"""Voicing selection helpers for AceFlow chord references."""

from __future__ import annotations

from typing import Optional

from .chord_parser import ParsedChord


def _pitch_candidates(pc: int, lo: int, hi: int) -> list[int]:
    """Return all MIDI notes with a given pitch class inside a range."""
    return [midi for midi in range(lo, hi + 1) if midi % 12 == pc]


def _best_bass_midi(pc: int, previous: Optional[int]) -> int:
    """Pick a bass note near the previous one while staying in a safe range."""
    candidates = _pitch_candidates(pc, 36, 55)
    target = previous if previous is not None else 43
    return min(candidates, key=lambda midi: (abs(midi - target), abs(midi - 43)))


def _compact_voicing(root_midi: int, intervals: list[int]) -> list[int]:
    """Compress a voiced chord into a midrange pad register."""
    voiced: list[int] = []
    for idx, interval in enumerate(intervals):
        midi = root_midi + interval
        while midi < 55:
            midi += 12
        while midi > 76:
            midi -= 12
        while idx > 0 and midi <= voiced[-1]:
            midi += 12
        voiced.append(midi)
    for idx in range(1, len(voiced)):
        while voiced[idx] - voiced[0] > 14 and voiced[idx] - 12 > voiced[idx - 1]:
            voiced[idx] -= 12
    voiced = sorted(voiced)
    return [min(79, max(54, midi)) for midi in voiced]


def choose_voicing(
    chord: ParsedChord,
    previous_pad: Optional[list[int]],
    previous_bass: Optional[int],
) -> tuple[int, list[int]]:
    """Choose a bass note and compact pad voicing for a parsed chord."""
    bass_midi = _best_bass_midi(chord.bass_pc, previous_bass)
    intervals = sorted({(pc - chord.root_pc) % 12 for pc in chord.chord_pcs})
    candidate_roots = _pitch_candidates(chord.root_pc, 55, 67) or [60]
    prev_pad = previous_pad or [60, 64, 67]
    prev_center = sum(prev_pad) / len(prev_pad)
    best_pad = None
    best_score = None
    for root_midi in candidate_roots:
        for inversion in range(len(intervals)):
            rotated = intervals[inversion:] + [value + 12 for value in intervals[:inversion]]
            pad = _compact_voicing(root_midi, rotated)
            if len(pad) >= 5:
                pad = [pad[0], pad[1], pad[2], pad[-1]]
            if len(pad) < 3:
                continue
            center = sum(pad) / len(pad)
            spread = pad[-1] - pad[0]
            leap = sum(abs(midi - prev_pad[min(i, len(prev_pad) - 1)]) for i, midi in enumerate(pad))
            score = abs(center - 64.5) + abs(center - prev_center) * 0.8 + spread * 0.35 + leap * 0.55
            if best_score is None or score < best_score:
                best_score = score
                best_pad = pad
    return bass_midi, (best_pad or [60, 64, 67])
