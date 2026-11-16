"""Original submission BEV drawing and sampling functions, retained unchanged.
Source file SHA-256: 566564c7d3c712ef915479103327f5574b8ec7c27e57b53fd9abc9af24301461
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
BG, REF, SIM = "#101827", "#47c7ec", "#ffab54"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def sample(reference, t):
    """Interpolate within the reference lifetime, without endpoint extrapolation.

    Args:
        reference: Immutable reference track with timestamped states.
        t: Scenario time in seconds.
    """
    s = reference["states"]
    if not s["t"][0] <= t <= s["t"][-1]:
        return None
    x, y = [float(np.interp(t, s["t"], s[k])) for k in ("x", "y")]
    yaw = float(np.interp(t, s["t"], np.unwrap(s["yaw"])))
    return [x, y, yaw, reference["bbox"]["length"], reference["bbox"]["width"]]

def draw_bev(canvas, data, frame, rect, selected=None):
    """Draw both box states and true-scale same-time error connectors in map space.

    Args:
        canvas: Pillow image receiving the clipped BEV panel.
        data: Joined map, actor states and coverage data.
        frame: Matched reference and measured states at one timestamp.
        rect: Drawing rectangle as left, top, width, height.
        selected: Optional actor index to draw alone.
    """
    _, _, width, height = rect
    viewport = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(viewport)
    left, top = 0, 0
    bounds = data["bounds"]
    scale = min(width / (bounds[2] - bounds[0]), height / (bounds[3] - bounds[1]))
    cx, cy = (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2

    def point(p):
        """Project a map point into image coordinates.

        Args:
            p: Map-space point in metres.
        """
        return (left + width / 2 + (p[0] - cx) * scale, top + height / 2 - (p[1] - cy) * scale)

    cone = data.get("cone")
    if cone:
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        poly = [point(p) for p in cone]
        rgb = (112, 237, 145) if data.get("cone_active", True) else (150, 160, 175)
        odraw.polygon(poly, fill=rgb + (34 if data.get("cone_active", True) else 20,))
        odraw.line(poly + [poly[0]], fill=rgb + (140 if data.get("cone_active", True) else 90,), width=2)
        viewport.paste(Image.alpha_composite(viewport.convert("RGBA"), overlay).convert("RGB"))
        draw = ImageDraw.Draw(viewport)
    for line in data["roads"]:
        draw.line([point(p) for p in line], fill=data.get("road_color", "#34435b"), width=data.get("road_width", 1))
    sr = data.get("sensor_range")
    if sr:
        (scx, scy), srad = sr
        n = 180
        for k in range(0, n, 2):  # dotted circle: draw every other segment
            a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            draw.line([point((scx + srad * math.cos(a0), scy + srad * math.sin(a0))),
                       point((scx + srad * math.cos(a1), scy + srad * math.sin(a1)))], fill="#c9d2e0", width=2)

    for i, actor in enumerate(data["actors"]):
        if selected is not None and i != selected:
            continue
        if len(actor["path"]) > 1:
            draw.line([point(p) for p in actor["path"]], fill="#254757", width=1)
        ref, actual = frame["r"][i], frame["a"][i]
        if ref and actual:
            draw.line(
                [point(ref), point(actual)], fill="#ed6470" if actual[5] > 2 else "#d8cf84", width=2
            )
        actual_color = "#6b7890" if actor["id"] in data.get("context_ids", ()) else SIM
        for state, color in ((ref, REF), (actual, actual_color)):
            if not state:
                continue
            if data.get("heading_arrows") and state is actual and actor["id"] == "ego":
                # small heading arrow from the box centre (simulation state only)
                hx, hy, hyaw = state[:3]
                hl = 4.0 if actor["id"] == "ego" else max(2.0, 0.45 * state[3])
                tip = (hx + hl * math.cos(hyaw), hy + hl * math.sin(hyaw))
                p0, p1 = point((hx, hy)), point(tip)
                draw.line([p0, p1], fill=color, width=2)
                ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
                for da in (2.6, -2.6):
                    draw.line([p1, (p1[0] + 6 * math.cos(ang + da), p1[1] + 6 * math.sin(ang + da))], fill=color, width=2)
            if actor["id"] == "ego":
                px, py = point(state)
                draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=color)
                continue
            x, y, yaw, length, breadth = state[:5]
            vertices = []
            for dx, dy in (
                (-length / 2, -breadth / 2),
                (length / 2, -breadth / 2),
                (length / 2, breadth / 2),
                (-length / 2, breadth / 2),
            ):
                vertices.append(
                    point(
                        (
                            x + dx * math.cos(yaw) - dy * math.sin(yaw),
                            y + dx * math.sin(yaw) + dy * math.cos(yaw),
                        )
                    )
                )
            draw.line(vertices + [vertices[0]], fill=color, width=2)
        if actual and ref and actual[5] > 2:
            draw.text(
                point(actual),
                f"{i}: {actual[5]:.1f}m",
                fill="white",
                font=ImageFont.truetype(FONT, 12),
            )
        if actual and actor['id'] in data.get('reactive_ids', ()):
            px,py=point(actual)
            draw.text((px-8,py-16),'R',fill='#70ed91',font=ImageFont.truetype(FONT,14))
    draw.line(
        (left + 20, top + height - 20, left + 20 + 10 * scale, top + height - 20),
        fill="white",
        width=3,
    )
    draw.text(
        (left + 20, top + height - 42),
        "10 m · north up",
        fill="white",
        font=ImageFont.truetype(FONT, 15),
    )
    canvas.paste(viewport, (rect[0], rect[1]))
