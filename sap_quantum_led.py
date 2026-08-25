#!/usr/bin/env python3
"""
SAP Quantum LED — standalone RasQberry external demo

Displays the SAP logo on any RasQberry LED matrix with three quantum-driven
color modes that cycle automatically:
  1. Per-LED quantum color  — each lit pixel gets its own quantum-random hue
  2. Per-row quantum stripe — each row shares one quantum-random hue
  3. Single quantum color   — the whole logo is one quantum-random hue

Quantum randomness: a 3-qubit H-gate circuit is measured shots=n times;
each 3-bit outcome maps to one of 8 palette entries.

Fallback: uses Python's random module when Qiskit / qiskit-aer is absent.

Usage: sudo python3 sap_quantum_led.py
"""

import sys
import time
import random
from typing import Tuple, List, Dict
from pathlib import Path

# Locate rq_led_utils in standard RasQberry install locations
for _candidate in [
    Path('/usr/bin'),
    Path('/usr/local/bin'),
    Path.home() / 'RasQberry-Two' / 'RQB2-bin',
    Path.home() / '.local' / 'bin',
    Path(__file__).resolve().parent.parent.parent / 'RQB2-bin',
]:
    if (_candidate / 'rq_led_utils.py').exists():
        sys.path.insert(0, str(_candidate))
        break

from rq_led_utils import (
    get_led_config,
    create_neopixel_strip,
    chunked_show,
    map_xy_to_pixel,
)

try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    _QUANTUM = True
except ImportError:
    _QUANTUM = False

# 8-entry palette — maps 3-bit outcomes 000…111 to colors
PALETTE: List[Tuple[int, int, int]] = [
    (0,   0,   255),   # 000 SAP blue
    (250,   1,   0),   # 001 red
    (2,  162,   4),    # 010 green
    (248, 223,   8),   # 011 yellow
    (0,  196, 173),    # 100 turquoise
    (251, 128, 191),   # 101 pink
    (249, 131,  31),   # 110 orange
    (131,  32, 158),   # 111 purple
]
COLOR_OFF: Tuple[int, int, int] = (0, 0, 0)
COLOR_BLUE = PALETTE[0]

# SAP logo pixel coordinates as (row, col) pairs.
# map_xy_to_pixel(col, row) handles panel orientation — no manual flip needed.
SAP_PIXELS: List[Tuple[int, int]] = [
    # Letter S
    (7, 0), (7, 1), (7, 2), (7, 3), (7, 4), (7, 5),
    (6, 0), (6, 1),
    (5, 0), (5, 1),
    (4, 0), (4, 1), (4, 2), (4, 3), (4, 4),
    (3, 2), (3, 3), (3, 4), (3, 5),
    (2, 4), (2, 5),
    (1, 4), (1, 5),
    (0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5),
    # Letter A
    (7, 10), (7, 11),
    (6,  9), (6, 12),
    (5,  8), (5, 13),
    (4,  8), (4,  9), (4, 10), (4, 11), (4, 12), (4, 13),
    (3,  8), (3, 13),
    (2,  8), (2, 13),
    (1,  8), (1, 13),
    (0,  8), (0, 13),
    # Letter P
    (7, 16), (7, 17), (7, 18), (7, 19), (7, 20),
    (6, 16), (6, 17), (6, 20), (6, 21),
    (5, 16), (5, 17), (5, 20), (5, 21),
    (4, 16), (4, 17), (4, 18), (4, 19), (4, 20),
    (3, 16), (3, 17),
    (2, 16), (2, 17),
    (1, 16), (1, 17),
    (0, 16), (0, 17),
]


def _quantum_measurements(n: int) -> List[str]:
    """Return a shuffled list of n 3-bit measurement strings from a quantum circuit."""
    sim = AerSimulator()
    qc = QuantumCircuit(3)
    qc.h(range(3))
    qc.measure_all()
    counts = sim.run(transpile(qc, sim), shots=n).result().get_counts()
    measurements: List[str] = []
    for outcome, count in counts.items():
        measurements.extend([outcome] * count)
    random.shuffle(measurements)
    return measurements


def quantum_colors(n: int) -> List[Tuple[int, int, int]]:
    """Return n quantum-random palette colors (falls back to pseudo-random)."""
    if not _QUANTUM:
        return [random.choice(PALETTE) for _ in range(n)]
    try:
        return [PALETTE[int(m, 2) % 8] for m in _quantum_measurements(n)]
    except Exception:
        return [random.choice(PALETTE) for _ in range(n)]


def draw_sap(pixels, color_by_coord: Dict[Tuple[int, int], Tuple[int, int, int]]) -> None:
    """Set each SAP logo LED to its color from color_by_coord."""
    for coord in SAP_PIXELS:
        row, col = coord
        idx = map_xy_to_pixel(col, row)
        if idx is not None:
            pixels[idx] = color_by_coord.get(coord, COLOR_BLUE)


def main() -> int:
    config = get_led_config()
    n_rows = config['matrix_height']
    n_leds = config['led_count']

    try:
        pixels = create_neopixel_strip(
            n_leds,
            config['pixel_order'],
            brightness=config['led_default_brightness'],
        )
    except Exception as exc:
        print(f"LED init failed: {exc}\nRun with sudo.", file=sys.stderr)
        return 1

    def clear() -> None:
        for i in range(n_leds):
            pixels[i] = COLOR_OFF
        chunked_show(pixels)

    mode = "quantum" if _QUANTUM else "pseudo-random"
    print(f"SAP Quantum LED  {config['matrix_width']}x{n_rows}  ({mode})")
    print("Ctrl+C to exit")

    try:
        while True:
            # Mode 1 — per-LED quantum color (each lit pixel independently random)
            colors = quantum_colors(len(SAP_PIXELS))
            clear()
            draw_sap(pixels, dict(zip(SAP_PIXELS, colors)))
            chunked_show(pixels)
            time.sleep(4.0)

            # Mode 2 — per-row quantum stripe (one quantum color per row)
            row_colors = quantum_colors(n_rows)
            row_map = dict(enumerate(row_colors))
            clear()
            draw_sap(pixels, {(r, c): row_map.get(r, COLOR_BLUE) for r, c in SAP_PIXELS})
            chunked_show(pixels)
            time.sleep(4.0)

            # Mode 3 — single quantum color for the whole logo
            solid = quantum_colors(1)[0]
            clear()
            draw_sap(pixels, {coord: solid for coord in SAP_PIXELS})
            chunked_show(pixels)
            time.sleep(4.0)

    except KeyboardInterrupt:
        pass
    finally:
        clear()

    return 0


if __name__ == '__main__':
    sys.exit(main())
