#!/usr/bin/env python3
"""Deterministic local renderer for the Bayer ultra-wide key visual."""

from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


SOURCE_W = 3840
SOURCE_H = 1280
CROP_TOP = 64
FINAL_H = 1152
OUTPUT = Path("output/imagegen/bayer-kv-local-render-3840x1152.png")
SEED = 1403155927

BG = np.array([6, 11, 7], dtype=np.float32) / 255.0
GREEN = np.array([154, 208, 76], dtype=np.float32) / 255.0
BLUE = np.array([80, 187, 249], dtype=np.float32) / 255.0


def srgb_to_linear(value: np.ndarray) -> np.ndarray:
    return np.where(value <= 0.04045, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, 0.0, 1.0)
    return np.where(value <= 0.0031308, value * 12.92, 1.055 * value ** (1.0 / 2.4) - 0.055)


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    u = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def catmull_rom(points: list[tuple[float, float]], samples_per_segment: int = 260) -> np.ndarray:
    p = np.asarray(points, dtype=np.float64)
    padded = np.vstack([p[0], p, p[-1]])
    chunks: list[np.ndarray] = []
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1 : i + 3]
        t = np.linspace(0.0, 1.0, samples_per_segment, endpoint=False)[:, None]
        curve = 0.5 * (
            2.0 * p1
            + (-p0 + p2) * t
            + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t**2
            + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t**3
        )
        chunks.append(curve)
    chunks.append(p[-1][None, :])
    return np.vstack(chunks)


def arc_length_path(points: list[tuple[float, float]], count: int = 4096) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dense = catmull_rom(points)
    seg = np.linalg.norm(np.diff(dense, axis=0), axis=1)
    cumulative = np.r_[0.0, np.cumsum(seg)]
    target = np.linspace(0.0, cumulative[-1], count)
    x = np.interp(target, cumulative, dense[:, 0])
    y = np.interp(target, cumulative, dense[:, 1])
    path = np.column_stack([x, y]).astype(np.float32)
    tangent = np.gradient(path, axis=0)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-5)
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    return path, tangent, normal


def deposit_bilinear(field: np.ndarray, x: np.ndarray, y: np.ndarray, weight: np.ndarray) -> None:
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    fx = x - x0
    fy = y - y0
    for dx, dy, factor in (
        (0, 0, (1.0 - fx) * (1.0 - fy)),
        (1, 0, fx * (1.0 - fy)),
        (0, 1, (1.0 - fx) * fy),
        (1, 1, fx * fy),
    ):
        xx = x0 + dx
        yy = y0 + dy
        valid = (xx >= 0) & (xx < SOURCE_W) & (yy >= 0) & (yy < SOURCE_H)
        np.add.at(field, (yy[valid], xx[valid]), (weight * factor)[valid])


def blur_field(field: np.ndarray, radius: float, scale: float = 1.0) -> np.ndarray:
    encoded = np.clip(field * scale * 255.0, 0.0, 255.0).astype(np.uint8)
    image = Image.fromarray(encoded, mode="L").filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(image, dtype=np.float32) / (255.0 * scale)


def draw_filaments(
    rng: np.random.Generator,
    path: np.ndarray,
    normal: np.ndarray,
    width: np.ndarray,
    count: int,
    core: bool,
) -> np.ndarray:
    layer = Image.new("L", (SOURCE_W, SOURCE_H), 0)
    draw = ImageDraw.Draw(layer)
    n = len(path)
    u = np.linspace(0.0, 1.0, n, dtype=np.float32)
    stride = 5
    for _ in range(count):
        if core:
            base = rng.normal(0.0, 0.11)
            alpha = int(rng.uniform(7, 18))
        else:
            base = np.clip(rng.normal(0.0, 0.62), -1.55, 1.55)
            alpha = int(rng.uniform(2, 8))
        phase = rng.uniform(0.0, math.tau)
        cycles = rng.uniform(0.65, 2.4)
        waviness = rng.uniform(0.02, 0.12)
        offset_factor = base + waviness * np.sin(math.tau * cycles * u + phase)
        offset_factor += 0.025 * np.sin(math.tau * (cycles * 4.1) * u + phase * 0.37)
        shifted = path + normal * (width * offset_factor)[:, None]
        start = int(rng.uniform(0.0, 0.10) * n)
        end = int(rng.uniform(0.84, 1.0) * n)
        pts = [tuple(map(float, p)) for p in shifted[start:end:stride]]
        if len(pts) > 2:
            draw.line(pts, fill=alpha, width=1, joint="curve")
    return np.asarray(layer, dtype=np.float32) / 255.0


def stream_field(
    rng: np.random.Generator,
    points: list[tuple[float, float]],
    crossing_t: tuple[float, ...],
    energy: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    path, tangent, normal = arc_length_path(points)
    u_path = np.linspace(0.0, 1.0, len(path), dtype=np.float32)
    width = (
        32.0
        + 62.0 * np.maximum(np.sin(np.pi * np.clip(u_path, 0.0, 1.0)), 0.0) ** 1.2
        + 38.0 * np.exp(-0.5 * ((u_path - 0.50) / 0.20) ** 2)
        + 13.0 * np.sin(math.tau * (1.35 * u_path + 0.13))
    ).astype(np.float32)
    width = np.maximum(width, 18.0)

    n_particles = 52000
    selector = rng.random(n_particles)
    t = rng.beta(1.12, 1.18, n_particles)
    if crossing_t:
        focused = selector < 0.22
        centers = rng.choice(np.asarray(crossing_t), focused.sum())
        t[focused] = np.clip(rng.normal(centers, 0.075), 0.0, 1.0)
    index_float = t * (len(path) - 1)
    index = np.clip(index_float.astype(np.int32), 0, len(path) - 1)

    mix = rng.random(n_particles)
    spread = np.where(
        mix < 0.72,
        rng.normal(0.0, 0.28, n_particles),
        np.where(mix < 0.96, rng.normal(0.0, 0.70, n_particles), rng.normal(0.0, 1.38, n_particles)),
    )
    local_width = width[index]
    offset = spread * local_width
    longitudinal = rng.normal(0.0, 2.3 + 4.0 * np.abs(spread), n_particles)
    xy = path[index] + normal[index] * offset[:, None] + tangent[index] * longitudinal[:, None]
    taper = smoothstep(0.0, 0.075, t) * (1.0 - smoothstep(0.90, 1.0, t))
    nucleus = np.zeros_like(t)
    for center in crossing_t:
        nucleus += np.exp(-0.5 * ((t - center) / 0.044) ** 2)
    intensity = energy * taper * (0.10 + 0.66 * rng.random(n_particles) ** 2.1)
    intensity *= np.exp(-0.32 * spread**2) * (1.0 + 0.75 * np.clip(nucleus, 0.0, 1.8))

    sharp = np.zeros((SOURCE_H, SOURCE_W), dtype=np.float32)
    deposit_bilinear(sharp, xy[:, 0], xy[:, 1], intensity)

    dust_count = 12500
    td = rng.beta(1.1, 1.15, dust_count)
    idxd = np.clip((td * (len(path) - 1)).astype(np.int32), 0, len(path) - 1)
    broad = rng.normal(0.0, 1.45, dust_count) * width[idxd]
    dust_xy = path[idxd] + normal[idxd] * broad[:, None]
    dust_xy += tangent[idxd] * rng.normal(0.0, 12.0, (dust_count, 1))
    dust_intensity = energy * rng.uniform(0.018, 0.11, dust_count)
    dust_intensity *= smoothstep(0.0, 0.09, td) * (1.0 - smoothstep(0.87, 1.0, td))
    dust_intensity *= np.exp(-0.16 * (broad / np.maximum(width[idxd], 1.0)) ** 2)
    dust = np.zeros_like(sharp)
    deposit_bilinear(dust, dust_xy[:, 0], dust_xy[:, 1], dust_intensity)

    filaments = draw_filaments(rng, path, normal, width, 180, core=False)
    core_filaments = draw_filaments(rng, path, normal, np.maximum(8.0, width * 0.17), 54, core=True)
    return sharp, dust, filaments, core_filaments


def add_colored(hdr: np.ndarray, field: np.ndarray, color_linear: np.ndarray, gain: float) -> None:
    hdr += field[:, :, None] * color_linear[None, None, :] * gain


def radial_haze(hdr: np.ndarray) -> None:
    yy, xx = np.mgrid[0:SOURCE_H, 0:SOURCE_W].astype(np.float32)
    blue_haze = np.exp(-(((xx - 1440.0) / 920.0) ** 2 + ((yy - 640.0) / 520.0) ** 2) * 1.7)
    green_haze = np.exp(-(((xx - 1760.0) / 760.0) ** 2 + ((yy - 760.0) / 420.0) ** 2) * 1.8)
    right_quiet = 1.0 - smoothstep(2600.0, 2900.0, xx)
    vertical = 1.0 - 0.22 * np.abs((yy - SOURCE_H / 2.0) / (SOURCE_H / 2.0))
    hdr += blue_haze[:, :, None] * srgb_to_linear(BLUE)[None, None, :] * 0.013 * right_quiet[:, :, None]
    hdr += green_haze[:, :, None] * srgb_to_linear(GREEN)[None, None, :] * 0.009 * right_quiet[:, :, None]
    hdr *= vertical[:, :, None]


def add_volumetric_rays(hdr: np.ndarray, rng: np.random.Generator) -> None:
    layer = Image.new("L", (SOURCE_W, SOURCE_H), 0)
    draw = ImageDraw.Draw(layer)
    origin = np.array([1650.0, 709.0])
    for _ in range(16):
        angle = rng.choice([rng.uniform(2.48, 3.56), rng.uniform(3.75, 4.55)])
        length = rng.uniform(450.0, 1450.0)
        spread = rng.uniform(0.004, 0.018)
        direction = np.array([math.cos(angle), math.sin(angle)])
        perpendicular = np.array([-direction[1], direction[0]])
        tip = origin + direction * length
        half = length * spread
        poly = [tuple(origin + perpendicular * 4), tuple(tip + perpendicular * half), tuple(tip - perpendicular * half), tuple(origin - perpendicular * 4)]
        draw.polygon(poly, fill=int(rng.uniform(7, 18)))
    blurred = np.asarray(layer.filter(ImageFilter.GaussianBlur(72.0)), dtype=np.float32) / 255.0
    add_colored(hdr, blurred, srgb_to_linear(np.array([0.45, 0.72, 1.0], dtype=np.float32)), 0.16)


def add_bokeh(
    hdr: np.ndarray,
    rng: np.random.Generator,
    points: list[tuple[float, float]],
    color_linear: np.ndarray,
    gain: float,
) -> None:
    path, tangent, normal = arc_length_path(points, count=2200)
    layer = Image.new("L", (SOURCE_W, SOURCE_H), 0)
    draw = ImageDraw.Draw(layer)
    for _ in range(620):
        t = float(rng.beta(1.25, 1.35))
        idx = min(len(path) - 1, int(t * (len(path) - 1)))
        width = 55.0 + 85.0 * math.sin(math.pi * t) ** 1.3
        offset = rng.normal(0.0, width * 0.95)
        along = rng.normal(0.0, 9.0)
        p = path[idx] + normal[idx] * offset + tangent[idx] * along
        radius = float(np.clip(rng.lognormal(0.35, 0.58), 1.0, 7.5))
        value = int(rng.uniform(5, 31) * (1.0 - 0.55 * radius / 7.5))
        draw.ellipse((p[0] - radius, p[1] - radius, p[0] + radius, p[1] + radius), fill=value)
    soft = np.asarray(layer.filter(ImageFilter.GaussianBlur(1.4)), dtype=np.float32) / 255.0
    add_colored(hdr, soft, color_linear, gain)


def render() -> None:
    started = time.perf_counter()
    rng = np.random.default_rng(SEED)
    bg_linear = srgb_to_linear(BG)
    hdr = np.empty((SOURCE_H, SOURCE_W, 3), dtype=np.float32)
    hdr[:] = bg_linear
    radial_haze(hdr)
    add_volumetric_rays(hdr, rng)

    blue_points = [
        (230, 920), (560, 875), (930, 780), (1280, 675), (1650, 709),
        (1920, 610), (2110, 485), (2030, 350), (1760, 280), (1450, 320),
        (1250, 470), (1330, 610), (1650, 709), (2040, 700), (2400, 590), (2725, 485),
    ]
    green_points = [
        (245, 1000), (600, 962), (970, 875), (1325, 775), (1650, 709),
        (1865, 635), (2075, 555), (2370, 515), (2720, 545),
    ]

    blue = stream_field(rng, blue_points, crossing_t=(0.285, 0.765), energy=1.00)
    green = stream_field(rng, green_points, crossing_t=(0.54,), energy=0.82)
    blue_linear = srgb_to_linear(BLUE)
    green_linear = srgb_to_linear(GREEN)

    for fields, color in ((blue, blue_linear), (green, green_linear)):
        sharp, dust, filaments, core = fields
        add_colored(hdr, sharp, color, 2.45)
        add_colored(hdr, blur_field(sharp, 0.75, 1.1), color, 0.82)
        add_colored(hdr, blur_field(sharp + dust * 2.0, 3.2, 1.2), color, 0.72)
        add_colored(hdr, blur_field(sharp + dust * 4.0 + filaments, 15.0, 1.6), color, 1.16)
        add_colored(hdr, blur_field(sharp + dust * 5.0 + filaments, 54.0, 2.2), color, 1.08)
        add_colored(hdr, dust, color, 3.4)
        add_colored(hdr, filaments, color, 0.58)
        add_colored(hdr, core, color, 1.38)

    add_bokeh(hdr, rng, blue_points, blue_linear, 2.0)
    add_bokeh(hdr, rng, green_points, green_linear, 1.65)

    # A tight, neutral crossing nucleus gives a focal spark without whitening the ribbons.
    nucleus = np.zeros((SOURCE_H, SOURCE_W), dtype=np.float32)
    count = 1650
    angle = rng.uniform(0.0, math.tau, count)
    radius = np.clip(rng.exponential(21.0, count), 0.0, 94.0)
    nx = 1650.0 + np.cos(angle) * radius * rng.uniform(0.55, 1.2, count)
    ny = 709.0 + np.sin(angle) * radius * rng.uniform(0.35, 0.92, count)
    ni = rng.uniform(0.08, 0.52, count) * np.exp(-radius / 58.0)
    deposit_bilinear(nucleus, nx, ny, ni)
    white_linear = srgb_to_linear(np.array([0.93, 0.98, 0.95], dtype=np.float32))
    add_colored(hdr, nucleus, white_linear, 2.35)
    add_colored(hdr, blur_field(nucleus, 7.0, 1.5), white_linear, 1.05)
    add_colored(hdr, blur_field(nucleus, 30.0, 3.0), white_linear, 0.72)

    # Protect the title field and crop-safe edges with a gradual optical falloff.
    yy, xx = np.mgrid[0:SOURCE_H, 0:SOURCE_W].astype(np.float32)
    title_falloff = 1.0 - smoothstep(2600.0, 2870.0, xx)
    edge_falloff = smoothstep(34.0, 150.0, yy) * (1.0 - smoothstep(SOURCE_H - 150.0, SOURCE_H - 34.0, yy))
    emission = hdr - bg_linear[None, None, :]
    hdr = bg_linear[None, None, :] + emission * title_falloff[:, :, None] * edge_falloff[:, :, None]

    # Filmic shoulder in linear space, then subtle vignette and one-LSB-scale dither.
    mapped = 1.0 - np.exp(-hdr * 1.18)
    dx = (xx - SOURCE_W * 0.48) / (SOURCE_W * 0.60)
    dy = (yy - SOURCE_H * 0.53) / (SOURCE_H * 0.78)
    vignette = np.clip(1.0 - 0.22 * (dx * dx + dy * dy), 0.72, 1.0)
    mapped *= vignette[:, :, None]
    srgb = linear_to_srgb(mapped)
    noise = rng.normal(0.0, 0.00135, srgb.shape[:2]).astype(np.float32)
    srgb += noise[:, :, None] * np.array([0.75, 1.0, 0.80], dtype=np.float32)
    srgb = np.clip(srgb, 0.0, 1.0)
    final = (srgb[CROP_TOP : CROP_TOP + FINAL_H] * 255.0 + 0.5).astype(np.uint8)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(final, mode="RGB").save(OUTPUT, format="PNG", optimize=True)
    elapsed = time.perf_counter() - started
    print(f"Saved {OUTPUT} ({SOURCE_W}x{FINAL_H}) in {elapsed:.2f}s")


if __name__ == "__main__":
    render()
