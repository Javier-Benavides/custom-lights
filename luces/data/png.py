"""Reads the small PNG images the satellite service sends, with no packages."""
import struct
import zlib

from .fetch import InvalidData

SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PIXELS = 65536


def read_png(data):
    """Pixels (r, g, b, a) of an 8-bit RGBA PNG."""
    if data[:8] != SIGNATURE:
        raise InvalidData("the image is not a PNG")
    position, compressed, width, height = 8, b"", 0, 0
    while position + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[position:position + 8])
        body = data[position + 8:position + 8 + length]
        if kind == b"IHDR":
            width, height, depth, mode, _, _, interlaced = struct.unpack(">IIBBBBB", body)
            if (depth, mode, interlaced) != (8, 6, 0) or not 0 < width * height <= MAX_PIXELS:
                raise InvalidData("PNG with an unexpected format")
        elif kind == b"IDAT":
            compressed += body
        position += 12 + length
    stride = width * 4
    try:
        raw = zlib.decompressobj().decompress(compressed, (stride + 1) * height)
    except zlib.error as e:
        raise InvalidData(f"damaged PNG: {e}") from e
    if not width or len(raw) != (stride + 1) * height:
        raise InvalidData("incomplete PNG")
    pixels, previous = [], bytearray(stride)
    for y in range(height):
        filter_type = raw[y * (stride + 1)]
        row = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        if filter_type > 4:
            raise InvalidData("PNG with an unknown filter")
        for i in range(stride):
            left = row[i - 4] if i >= 4 else 0
            up = previous[i]
            diagonal = previous[i - 4] if i >= 4 else 0
            if filter_type == 1:
                row[i] = (row[i] + left) & 255
            elif filter_type == 2:
                row[i] = (row[i] + up) & 255
            elif filter_type == 3:
                row[i] = (row[i] + (left + up) // 2) & 255
            elif filter_type == 4:
                p = left + up - diagonal
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - diagonal)
                row[i] = (row[i] + (left if pa <= pb and pa <= pc else up if pb <= pc else diagonal)) & 255
        pixels.extend(tuple(row[i:i + 4]) for i in range(0, stride, 4))
        previous = row
    return pixels
