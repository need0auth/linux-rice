#!/usr/bin/env python3
"""Generate the Hyprlock pixel panel with Python's standard library.

The artwork deliberately contains no clock, username, or password field;
Hyprlock renders those live, with real PAM authentication. All drawing lands
on an integer grid and the PNG is lossless. Run this script from any folder.
"""

from pathlib import Path
import struct
import zlib
from spidey_mask import MASK_PALETTE, mask_pixels


WIDTH, HEIGHT = 544, 588
COLORS = {
    "ink": "122743", "navy": "192450", "map": "16265e",
    "cyan": "49c7f4", "ice": "8ceaff", "blue": "348cd5",
    "coral": "ff958d", "red": "ed6e72", "peach": "ffd39a",
    "mint": "78ecb6", "green": "34cf8b", "paper": "fff0cc",
}
COLORS.update({name: color.lstrip("#") for name, color in MASK_PALETTE.items()})


def rgba(name, alpha=255):
    value = COLORS.get(name, name)
    return bytes((*bytes.fromhex(value), alpha))


class Canvas:
    def __init__(self):
        self.data = bytearray(WIDTH * HEIGHT * 4)

    def rect(self, x, y, width, height, color, alpha=255):
        pixel = rgba(color, alpha)
        start_x, end_x = max(0, x), min(WIDTH, x + width)
        if start_x >= end_x:
            return
        row = pixel * (end_x - start_x)
        for py in range(max(0, y), min(HEIGHT, y + height)):
            offset = (py * WIDTH + start_x) * 4
            self.data[offset:offset + len(row)] = row

    def stepped(self, x, y, width, height, step, color, alpha=255):
        self.rect(x + step, y, width - 2 * step, height, color, alpha)
        self.rect(x, y + step, width, height - 2 * step, color, alpha)

    def sprite(self, x, y, rows, palette, scale=2):
        for py, row in enumerate(rows):
            for px, key in enumerate(row):
                if key in palette:
                    self.rect(x + px * scale, y + py * scale,
                              scale, scale, palette[key])

    def save(self, path):
        def chunk(kind, data):
            return (struct.pack(">I", len(data)) + kind + data
                    + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

        rows = b"".join(b"\0" + self.data[y * WIDTH * 4:(y + 1) * WIDTH * 4]
                        for y in range(HEIGHT))
        contents = b"\x89PNG\r\n\x1a\n"
        contents += chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0))
        contents += chunk(b"IDAT", zlib.compress(rows, 9))
        contents += chunk(b"IEND", b"")
        path.write_bytes(contents)


def access_panel():
    c = Canvas()
    # A stepped outline, hard offset shadow and two-color bevel match the bars.
    c.stepped(8, 8, 536, 580, 8, "ink", 210)
    c.stepped(0, 0, 536, 580, 8, "ink")
    c.stepped(4, 4, 528, 572, 6, "cyan")
    c.rect(12, 8, 508, 4, "ice")
    c.rect(8, 12, 4, 552, "ice")
    c.rect(16, 72, 504, 488, "ink")
    c.rect(20, 76, 496, 480, "navy")
    c.rect(20, 76, 496, 4, "blue")
    c.rect(524, 16, 4, 548, "blue")
    c.rect(16, 568, 508, 4, "blue")

    # The same mask as the desktop SVG, at exact 2x pixels in the header.
    for (x, y), color in mask_pixels().items():
        c.rect(24 + x * 2, 12 + y * 2, 2, 2, color)

    # Header right-hand stepped marker and three little status pixels.
    for x, color in ((478, "mint"), (490, "peach"), (502, "coral")):
        c.rect(x, 24, 8, 8, "ink")
        c.rect(x + 2, 24, 6, 6, color)
    c.rect(478, 48, 32, 4, "ink")
    c.rect(490, 44, 20, 4, "ink")

    # Instrument ticks around the clock remain outside all live text bounds.
    for side in (36, 482):
        for y in range(116, 204, 12):
            c.rect(side, y, 14 if y % 24 == 20 else 8, 2, "blue")
    c.rect(72, 222, 392, 2, "blue")
    c.rect(72, 224, 80, 2, "cyan")

    # Username strip and its four-pixel mint locator.
    c.rect(40, 236, 456, 40, "ink")
    c.rect(44, 240, 448, 32, "map")
    c.rect(44, 240, 4, 32, "mint")
    c.rect(480, 248, 4, 4, "mint")
    c.rect(480, 260, 4, 4, "green")

    # Offset backing behind Hyprlock's live input field (416 x 60).
    c.rect(64, 342, 424, 64, "ink")
    for x in (40, 492):
        c.rect(x, 336, 4, 58, "blue")
        c.rect(x if x == 40 else x - 8, 336, 12, 4, "blue")

    # Static footer chips; all of their words are native Hyprlock labels.
    for x, base, shade in ((40, "coral", "red"), (288, "mint", "green")):
        c.stepped(x + 4, 470, 208, 32, 4, "ink")
        c.stepped(x, 466, 208, 32, 4, "ink")
        c.rect(x + 4, 470, 200, 24, base)
        c.rect(x + 8, 470, 192, 2, "paper")
        c.rect(x + 4, 490, 200, 4, shade)

    # Tiny pixel screws anchor the lower frame without adding soft shadows.
    for x in (28, 504):
        c.rect(x, 538, 8, 8, "ink")
        c.rect(x + 2, 540, 4, 2, "cyan")
    return c


def main():
    destination = Path(__file__).resolve().parents[1] / "config" / "hypr" / "lock-assets"
    destination.mkdir(parents=True, exist_ok=True)
    access_panel().save(destination / "access-panel.png")
    print(destination / "access-panel.png")


if __name__ == "__main__":
    main()
