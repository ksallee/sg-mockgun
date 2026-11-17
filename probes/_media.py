"""Tiny local files for the media probes: a 4x4 PNG and a short text file, in a temp folder."""
import os
import struct
import tempfile
import zlib


def png_bytes(size=4, rgb=(200, 40, 40)):
    """A valid RGB PNG of size x size pixels, built with zlib alone."""
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(rgb) * size for _ in range(size))
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def files():
    """Paths to `probe.png` and `probe.txt` in a fresh temp folder."""
    folder = tempfile.mkdtemp(prefix="sgprobe_")
    png = os.path.join(folder, "probe.png")
    txt = os.path.join(folder, "probe.txt")
    with open(png, "wb") as f:
        f.write(png_bytes())
    with open(txt, "w") as f:
        f.write("sg-mockgun probe file\n")
    return png, txt


def attachment_fields(sg):
    """Every field code on Attachment, sorted."""
    return sorted(sg.schema_field_read("Attachment"))


def url_shape(url):
    """A URL with its host and query replaced, so its path form can be recorded."""
    if not isinstance(url, str):
        return url
    import re
    host = re.match(r"^https?://([^/]+)", url)
    if host:
        name = host.group(1)
        kind = "<s3-host>" if "amazonaws" in name else "<site-host>" if ("shotgrid" in name or "shotgunstudio" in name) else "<other-host>"
        url = url.replace(host.group(0), kind, 1)
    url = re.sub(r"\?.*$", "?<query>", url)
    return re.sub(r"[0-9a-f]{16,}", "<hex>", url)


def shapes(value):
    """`value` with every string URL inside reduced by url_shape."""
    if isinstance(value, dict):
        return {k: shapes(v) for k, v in value.items()}
    if isinstance(value, list):
        return [shapes(v) for v in value]
    if isinstance(value, str) and value.startswith("http"):
        return url_shape(value)
    return value
