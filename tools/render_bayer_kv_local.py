#!/usr/bin/env python3
"""Render a deterministic Bayer blue/green particle-ribbon key visual."""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageCms, ImageDraw, ImageEnhance, ImageFilter


WIDTH = 3840
HEIGHT = 1152
GREEN = (154, 208, 76)
BLUE = (80, 187, 249)
BG = (5, 10, 7)
CROSSING = (1650.0, 645.0)


def cubic(p0, p1, p2, p3, t):
    u = 1.0 - t
    uu = u * u
    tt = t * t
    return (
        uu * u * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + tt * t * p3[0],
        uu * u * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + tt * t * p3[1],
    )


def cubic_derivative(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (
        3 * u * u * (p1[0] - p0[0])
        + 6 * u * t * (p2[0] - p1[0])
        + 3 * t * t * (p3[0] - p2[0]),
        3 * u * u * (p1[1] - p0[1])
        + 6 * u * t * (p2[1] - p1[1])
        + 3 * t * t * (p3[1] - p2[1]),
    )


BLUE_CURVES = (
    ((210, 790), (660, 1010), (1240, 855), CROSSING),
    (CROSSING, (1930, 270), (2450, 260), (2700, 660)),
)
GREEN_CURVES = (
    ((210, 680), (670, 500), (1240, 470), CROSSING),
    (CROSSING, (1920, 805), (2350, 1005), (2690, 815)),
)


def path_sample(curves, t):
    split = 0.46
    if t <= split:
        local = t / split
        curve = curves[0]
    else:
        local = (t - split) / (1.0 - split)
        curve = curves[1]
    x, y = cubic(*curve, local)
    dx, dy = cubic_derivative(*curve, local)
    length = max(math.hypot(dx, dy), 1e-6)
    return x, y, dx / length, dy / length, -dy / length, dx / length


def ribbon_width(t):
    body = math.sin(math.pi * max(0.0, min(1.0, t))) ** 0.72
    crossing_taper = 1.0 - 0.48 * math.exp(-((t - 0.46) / 0.095) ** 2)
    end_taper = min(1.0, t / 0.065, (1.0 - t) / 0.065)
    return (30.0 + 128.0 * body) * crossing_taper * max(0.15, end_taper)


def rgba_layer():
    return Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))


def alpha_composite(base, layer):
    return Image.alpha_composite(base, layer)


def tinted(color, factor, white_mix=0.0):
    return tuple(
        max(0, min(255, int(channel * factor * (1.0 - white_mix) + 255 * white_mix)))
        for channel in color
    )


def path_points(curves, count=760, offset_fn=None):
    points = []
    for i in range(count):
        t = i / (count - 1)
        x, y, tx, ty, nx, ny = path_sample(curves, t)
        offset = offset_fn(t) if offset_fn else 0.0
        points.append((int(round(x + nx * offset)), int(round(y + ny * offset))))
    return points


def add_background(base):
    ambient = rgba_layer()
    draw = ImageDraw.Draw(ambient, "RGBA")
    draw.ellipse((600, 250, 2700, 1100), fill=(25, 64, 43, 17))
    draw.ellipse((1000, 150, 2850, 980), fill=(24, 68, 105, 15))
    draw.ellipse((1050, 420, 2250, 900), fill=(92, 152, 110, 10))
    ambient = ambient.filter(ImageFilter.GaussianBlur(220))
    base = alpha_composite(base, ambient)

    rays = rgba_layer()
    ray_draw = ImageDraw.Draw(rays, "RGBA")
    cx, cy = CROSSING
    ray_draw.polygon(((cx, cy), (130, 925), (140, 1010)), fill=(68, 177, 242, 8))
    ray_draw.polygon(((cx, cy), (310, 440), (430, 410)), fill=(139, 204, 74, 7))
    ray_draw.polygon(((cx, cy), (2680, 210), (2740, 295)), fill=(66, 176, 246, 5))
    ray_draw.polygon(((cx, cy), (2700, 945), (2630, 1015)), fill=(143, 205, 75, 5))
    rays = rays.filter(ImageFilter.GaussianBlur(72))
    return alpha_composite(base, rays)


def add_stream_glow(base, curves, color):
    points = path_points(curves)
    specs = (
        (168, 14, 58),
        (92, 18, 34),
        (38, 30, 15),
        (13, 55, 6),
    )
    for width, alpha, blur in specs:
        layer = rgba_layer()
        draw = ImageDraw.Draw(layer, "RGBA")
        draw.line(points, fill=(*color, alpha), width=width, joint="curve")
        if blur:
            layer = layer.filter(ImageFilter.GaussianBlur(blur))
        base = alpha_composite(base, layer)
    return base


def add_strands(base, curves, color, rng, phase):
    mist = rgba_layer()
    mist_draw = ImageDraw.Draw(mist, "RGBA")
    crisp = rgba_layer()
    crisp_draw = ImageDraw.Draw(crisp, "RGBA")

    for index in range(112):
        base_offset = rng.gauss(0.0, 0.56)
        wave_phase = rng.uniform(0, math.tau)
        wave_freq = rng.uniform(1.2, 3.8)
        drift = rng.uniform(-11.0, 11.0)

        def offset_fn(t, bo=base_offset, wp=wave_phase, wf=wave_freq, dr=drift):
            envelope = ribbon_width(t)
            weave = math.sin(t * math.tau * wf + wp) * (5.0 + 4.0 * math.sin(math.pi * t))
            perspective = math.sin(t * math.pi + phase) * dr * math.sin(math.pi * t)
            return bo * envelope + weave + perspective

        points = path_points(curves, count=520, offset_fn=offset_fn)
        center_bias = max(0.0, 1.0 - abs(base_offset) / 1.55)
        factor = rng.uniform(0.62, 1.08) + 0.16 * center_bias
        line_color = tinted(color, factor, white_mix=0.025 * center_bias)
        if index < 70:
            mist_draw.line(
                points,
                fill=(*line_color, rng.randint(7, 17)),
                width=rng.choice((1, 2, 2, 3)),
                joint="curve",
            )
        else:
            crisp_draw.line(
                points,
                fill=(*line_color, rng.randint(28, 66)),
                width=rng.choice((1, 1, 2)),
                joint="curve",
            )

    mist = mist.filter(ImageFilter.GaussianBlur(2.2))
    base = alpha_composite(base, mist)
    return alpha_composite(base, crisp)


def particle_t(rng):
    choice = rng.random()
    if choice < 0.58:
        return max(0.0, min(1.0, rng.betavariate(2.8, 3.0)))
    if choice < 0.86:
        return rng.random()
    return max(0.0, min(1.0, rng.gauss(0.46, 0.075)))


def add_particles(base, curves, color, rng, count):
    haze = rgba_layer()
    haze_draw = ImageDraw.Draw(haze, "RGBA")
    crisp = rgba_layer()
    crisp_draw = ImageDraw.Draw(crisp, "RGBA")
    streaks = rgba_layer()
    streak_draw = ImageDraw.Draw(streaks, "RGBA")

    for _ in range(count):
        t = particle_t(rng)
        x, y, tx, ty, nx, ny = path_sample(curves, t)
        width = ribbon_width(t)
        spread = rng.gauss(0.0, 0.57)
        if rng.random() < 0.13:
            spread *= rng.uniform(1.5, 2.8)
        perpendicular = spread * width
        tangent_jitter = rng.gauss(0.0, 13.0 + 13.0 * math.sin(math.pi * t))
        px = x + nx * perpendicular + tx * tangent_jitter
        py = y + ny * perpendicular + ty * tangent_jitter
        if px < 175 or px > 2815 or py < 75 or py > 1070:
            continue

        depth = rng.random()
        cross_energy = math.exp(-((t - 0.46) / 0.11) ** 2)
        center_energy = math.exp(-0.5 * (spread / 0.72) ** 2)
        factor = rng.uniform(0.58, 1.10) + 0.23 * center_energy + 0.10 * cross_energy
        white_mix = 0.0
        if cross_energy > 0.72 and rng.random() < 0.035:
            white_mix = rng.uniform(0.08, 0.28)
        particle_color = tinted(color, factor, white_mix)
        alpha = int(20 + 145 * center_energy * (0.36 + 0.64 * depth))

        if depth < 0.055:
            radius = rng.uniform(3.2, 8.5)
            haze_draw.ellipse(
                (px - radius, py - radius, px + radius, py + radius),
                fill=(*particle_color, max(8, alpha // 4)),
            )
        elif rng.random() < 0.016:
            length = rng.uniform(6.0, 20.0)
            streak_draw.line(
                (px - tx * length * 0.35, py - ty * length * 0.35, px + tx * length, py + ty * length),
                fill=(*particle_color, min(150, alpha)),
                width=rng.choice((1, 1, 2)),
            )
        else:
            radius = rng.choices((0.55, 0.85, 1.15, 1.6, 2.2), (18, 31, 28, 17, 6))[0]
            crisp_draw.ellipse(
                (px - radius, py - radius, px + radius, py + radius),
                fill=(*particle_color, alpha),
            )

    haze = haze.filter(ImageFilter.GaussianBlur(5.5))
    base = alpha_composite(base, haze)
    base = alpha_composite(base, streaks.filter(ImageFilter.GaussianBlur(0.65)))
    return alpha_composite(base, crisp)


def add_crossing(base):
    cx, cy = CROSSING
    glow = rgba_layer()
    draw = ImageDraw.Draw(glow, "RGBA")
    draw.ellipse((cx - 190, cy - 92, cx + 190, cy + 92), fill=(115, 218, 205, 26))
    draw.ellipse((cx - 82, cy - 42, cx + 82, cy + 42), fill=(171, 236, 207, 46))
    glow = glow.filter(ImageFilter.GaussianBlur(38))
    base = alpha_composite(base, glow)

    core = rgba_layer()
    core_draw = ImageDraw.Draw(core, "RGBA")
    core_draw.ellipse((cx - 23, cy - 10, cx + 23, cy + 10), fill=(226, 251, 238, 90))
    core = core.filter(ImageFilter.GaussianBlur(8))
    return alpha_composite(base, core)


def add_local_dust(base, rng):
    layer = rgba_layer()
    draw = ImageDraw.Draw(layer, "RGBA")
    for _ in range(1150):
        angle = rng.uniform(0, math.tau)
        radius = abs(rng.gauss(0.0, 1.0)) ** 0.75
        x = CROSSING[0] + math.cos(angle) * radius * rng.uniform(150, 790)
        y = CROSSING[1] + math.sin(angle) * radius * rng.uniform(70, 280)
        if not (300 < x < 2780 and 100 < y < 1050):
            continue
        mix = rng.random()
        color = tuple(int(GREEN[i] * mix + BLUE[i] * (1 - mix)) for i in range(3))
        r = rng.choice((0.45, 0.6, 0.8, 1.0))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(*color, rng.randint(10, 48)))
    return alpha_composite(base, layer)


def finish(base):
    rgb = base.convert("RGB")
    rgb = ImageEnhance.Contrast(rgb).enhance(1.055)
    noise = Image.effect_noise((WIDTH, HEIGHT), 5.0).convert("L")
    noise_rgb = Image.merge(
        "RGB",
        (
            noise.point(lambda v: max(0, min(255, int(v * 0.033)))),
            noise.point(lambda v: max(0, min(255, int(v * 0.043)))),
            noise.point(lambda v: max(0, min(255, int(v * 0.036)))),
        ),
    )
    return ImageChops.add(rgb, noise_rgb, scale=1.0, offset=-4)


def render(seed):
    rng = random.Random(seed)
    base = Image.new("RGBA", (WIDTH, HEIGHT), (*BG, 255))
    base = add_background(base)

    base = add_stream_glow(base, BLUE_CURVES, BLUE)
    base = add_stream_glow(base, GREEN_CURVES, GREEN)
    base = add_strands(base, BLUE_CURVES, BLUE, rng, 0.0)
    base = add_strands(base, GREEN_CURVES, GREEN, rng, 1.7)
    base = add_particles(base, BLUE_CURVES, BLUE, rng, 12200)
    base = add_particles(base, GREEN_CURVES, GREEN, rng, 12200)
    base = add_local_dust(base, rng)
    base = add_crossing(base)
    return finish(base)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="output/imagegen/bayer-kv-local-3840x1152.png",
        help="Destination PNG path",
    )
    parser.add_argument("--seed", type=int, default=20261020)
    args = parser.parse_args()

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = render(args.seed)
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    image.save(output, format="PNG", optimize=True, icc_profile=profile)
    print(f"Wrote {output} ({image.width}x{image.height}, {image.mode})")


if __name__ == "__main__":
    main()
