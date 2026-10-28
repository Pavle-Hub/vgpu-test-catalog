"""Render the small drawing format using Windows GDI; encode PNG with stdlib."""

from __future__ import annotations

import ctypes as ct
import struct
import sys
import zlib
from pathlib import Path
from typing import Any


def png_bytes(width: int, height: int, rgb: bytes) -> bytes:
    if len(rgb) != width * height * 3:
        raise ValueError("RGB buffer size does not match dimensions.")

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    rows = b"".join(b"\0" + rgb[y * width * 3:(y + 1) * width * 3] for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"pHYs", struct.pack(">IIB", 11811, 11811, 1))  # 300 dpi
        + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")
    )


def render(drawing: dict[str, Any], target: Path) -> None:
    if sys.platform != "win32":
        raise OSError("PNG rendering uses Windows GDI; use the portable SVG on other systems.")
    if target.exists():
        raise FileExistsError(target)
    gdi = ct.WinDLL("gdi32", use_last_error=True)
    ptr, integer, uint = ct.c_void_p, ct.c_int, ct.c_uint32

    def api(name: str, restype: Any, args: list[Any]) -> Any:
        function = getattr(gdi, name)
        function.restype, function.argtypes = restype, args
        return function

    dc_create = api("CreateCompatibleDC", ptr, [ptr])
    dib_create = api("CreateDIBSection", ptr, [ptr, ptr, uint, ct.POINTER(ptr), ptr, uint])
    select = api("SelectObject", ptr, [ptr, ptr])
    delete = api("DeleteObject", integer, [ptr])
    dc_delete = api("DeleteDC", integer, [ptr])
    brush_create = api("CreateSolidBrush", ptr, [uint])
    pen_create = api("CreatePen", ptr, [integer, integer, uint])
    font_create = api("CreateFontW", ptr, [integer] * 5 + [uint] * 8 + [ct.c_wchar_p])
    text_out = api("TextOutW", integer, [ptr, integer, integer, ct.c_wchar_p, integer])
    move = api("MoveToEx", integer, [ptr, integer, integer, ptr])
    line = api("LineTo", integer, [ptr, integer, integer])
    ellipse = api("Ellipse", integer, [ptr, integer, integer, integer, integer])
    rectangle = api("Rectangle", integer, [ptr, integer, integer, integer, integer])
    text_color = api("SetTextColor", uint, [ptr, uint])
    background = api("SetBkMode", integer, [ptr, integer])
    flush = api("GdiFlush", integer, [])
    width, height = drawing["width"] * 2, drawing["height"] * 2
    # Top-down, 32-bit uncompressed DIB. The final PNG has opaque RGB pixels.
    info = ct.create_string_buffer(struct.pack(
        "<IiiHHIIiiII", 40, width, -height, 1, 32, 0, width * height * 4, 0, 0, 0, 0
    ))
    dc, bits = dc_create(None), ptr()
    bitmap = dib_create(dc, info, 0, ct.byref(bits), None, 0)
    if not dc or not bitmap or not bits:
        if bitmap:
            delete(bitmap)
        if dc:
            dc_delete(dc)
        raise OSError("Could not allocate the chart bitmap.")
    original_bitmap = select(dc, bitmap)
    try:
        ct.memset(bits, 255, width * height * 4)
        background(dc, 1)
        for item in drawing["shapes"]:
            color_hex = item["color"].lstrip("#")
            red, green, blue = (int(color_hex[n:n + 2], 16) for n in (0, 2, 4))
            color = red | green << 8 | blue << 16
            x, y = round(item["x"] * 2), round(item["y"] * 2)
            objects, previous = [], []
            try:
                if item["type"] == "text":
                    font = font_create(-item["size"] * 2, 0, 0, 0, 400,
                                       0, 0, 0, 1, 0, 0, 4, 0, "Segoe UI")
                    objects.append(font)
                    previous.append(select(dc, font))
                    text_color(dc, color)
                    text_out(dc, x, y, item["text"], len(item["text"]))
                else:
                    pen = pen_create(0, item.get("width", 1) * 2, color)
                    objects.append(pen)
                    previous.append(select(dc, pen))
                    if item["type"] == "line":
                        move(dc, x, y, None)
                        line(dc, round(item["x2"] * 2), round(item["y2"] * 2))
                    else:
                        brush = brush_create(color)
                        objects.append(brush)
                        previous.append(select(dc, brush))
                        draw = rectangle if item["square"] else ellipse
                        draw(dc, x - 12, y - 12, x + 12, y + 12)
            finally:
                for old in reversed(previous):
                    select(dc, old)
                for handle in objects:
                    delete(handle)
        flush()
        bgra = ct.string_at(bits, width * height * 4)
        rgb = bytearray(width * height * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = bgra[2::4], bgra[1::4], bgra[0::4]
        target.write_bytes(png_bytes(width, height, rgb))
    finally:
        select(dc, original_bitmap)
        delete(bitmap)
        dc_delete(dc)
