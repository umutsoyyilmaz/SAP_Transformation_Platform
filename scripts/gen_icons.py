"""Generate placeholder PWA icons."""
import struct, zlib

def create_png(size, bg_r=53, bg_g=74, bg_b=95):
    width = height = size
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'
        for x in range(width):
            cx, cy = width // 2, height // 2
            r = min(width, height) * 0.35
            dx, dy = x - cx, y - cy
            dist = (dx*dx + dy*dy) ** 0.5
            if dist < r:
                raw_data += bytes([255, 255, 255])
            else:
                raw_data += bytes([bg_r, bg_g, bg_b])

    def make_chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    sig += make_chunk(b'IHDR', ihdr)
    compressed = zlib.compress(raw_data)
    sig += make_chunk(b'IDAT', compressed)
    sig += make_chunk(b'IEND', b'')
    return sig

for size in [72, 96, 128, 144, 152, 192, 384, 512]:
    data = create_png(size)
    with open(f'static/icons/icon-{size}.png', 'wb') as f:
        f.write(data)
    print(f'Created icon-{size}.png ({len(data)} bytes)')
