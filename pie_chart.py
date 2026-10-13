"""Dependency-free pie chart rendered straight to PNG bytes (no Pillow/matplotlib needed)."""
import math
import struct
import zlib


def _rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def pie_png(values, colors, size=360, supersample=4):
    """values/colors are parallel lists; colors are 'RRGGBB'. Slices run clockwise from 12 o'clock."""
    total = sum(values)
    slices, start = [], 0.0
    for value, color in zip(values, colors):
        if value > 0:
            end = start + 2 * math.pi * value / total
            slices.append((end, _rgb(color)))
            start = end
    center, radius = size / 2, size / 2 - 2
    edges = [0.0] + [end for end, _ in slices]
    white = (255, 255, 255)
    offsets = [(k + 0.5) / supersample for k in range(supersample)]

    def sample(px, py):
        dx, dy = px - center, py - center
        if math.hypot(dx, dy) > radius or not slices:
            return white
        angle = math.atan2(dx, -dy) % (2 * math.pi)
        return next((c for end, c in slices if angle <= end), slices[-1][1])

    rows = []
    for y in range(size):
        row = bytearray([0])  # PNG filter type: none
        for x in range(size):
            dx, dy = x + 0.5 - center, y + 0.5 - center
            dist = math.hypot(dx, dy)
            angle = math.atan2(dx, -dy) % (2 * math.pi)
            near_edge = abs(dist - radius) < 1.5 or (len(slices) > 1 and dist < radius + 1.5 and min(
                abs((angle - e + math.pi) % (2 * math.pi) - math.pi) for e in edges) * dist < 1.5)
            if not near_edge:
                row += bytes(sample(x + 0.5, y + 0.5))
                continue
            # Anti-alias only the rim and slice borders; averaging against white keeps the PNG opaque.
            colors = [sample(x + ox, y + oy) for oy in offsets for ox in offsets]
            row += bytes(round(sum(c[i] for c in colors) / len(colors)) for i in range(3))
        rows.append(bytes(row))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b'')
