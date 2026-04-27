"""Auto-generated tool module."""

from __future__ import annotations

import json
import colorsys


def run(payload: str) -> str:
    """Convert colors between HEX, RGB, HSL formats, or generate color palettes."""
    try:
        data = json.loads(payload)
        mode = str(data.get("mode", "convert")).lower().strip()
    except (json.JSONDecodeError, TypeError):
        return "error: invalid payload"

    if mode == "convert":
        color_input = str(data.get("color", "")).strip()
        if not color_input:
            return "error: 'color' is required for convert mode"

        if color_input.startswith("#"):
            hex_val = color_input.lstrip("#")
            if len(hex_val) == 3:
                hex_val = "".join(c * 2 for c in hex_val)
            if len(hex_val) != 6:
                return "error: invalid hex color"
            r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
        elif color_input.startswith("rgb"):
            import re
            nums = re.findall(r"\d+", color_input)
            if len(nums) < 3:
                return "error: invalid rgb color"
            r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
        elif color_input.startswith("hsl"):
            import re
            nums = re.findall(r"[\d.]+", color_input)
            if len(nums) < 3:
                return "error: invalid hsl color"
            h, s, l = float(nums[0]) / 360, float(nums[1]) / 100, float(nums[2]) / 100
            r, g, b = [round(c * 255) for c in colorsys.hls_to_rgb(h, l, s)]
        else:
            return "error: unrecognized color format. Use #hex, rgb(r,g,b), or hsl(h,s%,l%)"

        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        return json.dumps({
            "hex": f"#{r:02x}{g:02x}{b:02x}",
            "rgb": f"rgb({r}, {g}, {b})",
            "hsl": f"hsl({round(h * 360)}, {round(s * 100)}%, {round(l * 100)}%)",
            "channels": {"r": r, "g": g, "b": b},
        }, indent=2)

    elif mode == "palette":
        count = min(int(data.get("count", 5)), 20)
        base_hue = float(data.get("hue", 0)) / 360
        colors = []
        for i in range(count):
            h = (base_hue + i / count) % 1.0
            r, g, b = [round(c * 255) for c in colorsys.hls_to_rgb(h, 0.5, 0.7)]
            colors.append(f"#{r:02x}{g:02x}{b:02x}")
        return json.dumps({"palette": colors}, indent=2)

    elif mode == "complementary":
        color_input = str(data.get("color", "")).strip()
        if not color_input.startswith("#"):
            return "error: provide color as #hex for complementary mode"
        hex_val = color_input.lstrip("#")
        if len(hex_val) == 3:
            hex_val = "".join(c * 2 for c in hex_val)
        r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        comp_h = (h + 0.5) % 1.0
        cr, cg, cb = [round(c * 255) for c in colorsys.hls_to_rgb(comp_h, l, s)]
        return json.dumps({
            "original": f"#{r:02x}{g:02x}{b:02x}",
            "complementary": f"#{cr:02x}{cg:02x}{cb:02x}",
        }, indent=2)

    return f"error: unknown mode '{mode}'. Use: convert, palette, complementary"


TOOL_SPEC = {
    "name": "color_tool",
    "description": "Convert colors between HEX, RGB, and HSL formats. Generate color palettes and find complementary colors.",
    "category": "visualization",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "description": "Operation mode: convert (format conversion), palette (generate palette), complementary (find complementary).",
                "enum": ["convert", "palette", "complementary"]
            },
            "color": {
                "type": "string",
                "description": "Color value in #hex, rgb(r,g,b), or hsl(h,s%,l%) format."
            },
            "count": {
                "type": "integer",
                "description": "Number of colors in palette (default: 5, max: 20)."
            },
            "hue": {
                "type": "number",
                "description": "Base hue value in degrees (0-360) for palette generation."
            }
        },
        "required": ["mode"]
    }
}
