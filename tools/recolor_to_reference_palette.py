#!/usr/bin/env python3
"""Recolor a JPEG without changing its pixel geometry.

The transform preserves every source pixel's linear-light luminance while
replacing its chroma with a smooth magenta -> violet -> blue -> cyan field.
Neutral highlights are kept close to white so logos and UI linework remain
clean. The source JPEG's quantization tables and 4:2:0 sampling are reused.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, JpegImagePlugin


# Colors sampled from the supplied palette reference, ordered from the
# reference's lower-left corner toward its upper-right corner.
PALETTE_STOPS = np.array(
    [
        [0.00, 0xC3, 0x22, 0x60],  # rose-magenta
        [0.27, 0x76, 0x5A, 0x9D],  # violet
        [0.50, 0x56, 0x74, 0xB7],  # blue-violet
        [0.74, 0x36, 0x8E, 0xD2],  # blue
        [1.00, 0x05, 0xB5, 0xF9],  # bright cyan-blue
    ],
    dtype=np.float32,
)


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(rgb: np.ndarray) -> np.ndarray:
    rgb = np.clip(rgb, 0.0, 1.0)
    return np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * rgb ** (1.0 / 2.4) - 0.055)


def smoothstep(edge0: float, edge1: float, value: np.ndarray) -> np.ndarray:
    t = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def palette_field(width: int, height: int) -> np.ndarray:
    """Build the reference-like diagonal color field at source resolution."""
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    # Lower-left maps to magenta; upper-right maps to cyan-blue.
    position = np.clip(0.55 * x + 0.45 * (1.0 - y), 0.0, 1.0)

    stop_positions = PALETTE_STOPS[:, 0]
    stop_colors = PALETTE_STOPS[:, 1:] / 255.0
    result = np.empty((height, width, 3), dtype=np.float32)
    for channel in range(3):
        result[..., channel] = np.interp(
            position.ravel(), stop_positions, stop_colors[:, channel]
        ).reshape(height, width)
    return result


def recolor(source: Image.Image) -> Image.Image:
    src_srgb = np.asarray(source.convert("RGB"), dtype=np.float32) / 255.0
    height, width = src_srgb.shape[:2]

    src_linear = srgb_to_linear(src_srgb)
    luminance = np.sum(
        src_linear * np.array([0.2126, 0.7152, 0.0722], dtype=np.float32), axis=2
    )

    palette_srgb = palette_field(width, height)
    palette_linear = srgb_to_linear(palette_srgb)
    palette_luminance = np.sum(
        palette_linear * np.array([0.2126, 0.7152, 0.0722], dtype=np.float32), axis=2
    )

    # Follow a black -> palette color -> white ray. At every point the output
    # has the exact same linear-light luminance as the corresponding source
    # pixel, preserving shading, texture, linework, and glow falloff.
    below = luminance <= palette_luminance
    dark_scale = luminance / np.maximum(palette_luminance, 1e-6)
    light_scale = (luminance - palette_luminance) / np.maximum(
        1.0 - palette_luminance, 1e-6
    )
    chromatic = np.where(
        below[..., None],
        palette_linear * dark_scale[..., None],
        palette_linear + (1.0 - palette_linear) * light_scale[..., None],
    )

    # Preserve neutral whites and pale gray UI elements. Colored pixels receive
    # the full palette; neutral dark areas still gain a subtle cool atmosphere.
    src_max = np.max(src_srgb, axis=2)
    src_min = np.min(src_srgb, axis=2)
    saturation = (src_max - src_min) / np.maximum(src_max, 1e-5)
    colorfulness = smoothstep(0.025, 0.32, saturation)
    highlight = smoothstep(0.64, 0.96, luminance)
    strength = (0.42 + 0.58 * colorfulness) * (1.0 - 0.86 * highlight)

    neutral = np.repeat(luminance[..., None], 3, axis=2)
    out_linear = neutral + strength[..., None] * (chromatic - neutral)
    out_srgb = linear_to_srgb(out_linear)
    out_u8 = np.rint(out_srgb * 255.0).astype(np.uint8)
    return Image.fromarray(out_u8, mode="RGB")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with Image.open(args.source) as source:
        source.load()
        if source.format != "JPEG":
            raise ValueError(f"Expected JPEG source, got {source.format!r}")
        original_size = source.size
        qtables = source.quantization
        result = recolor(source)

    if result.size != original_size:
        raise RuntimeError("Recolor unexpectedly changed the source dimensions")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.save(
        args.output,
        format="JPEG",
        qtables=qtables,
        subsampling=2,
        progressive=False,
        optimize=False,
    )

    with Image.open(args.output) as check:
        check.load()
        print(f"saved={args.output}")
        print(f"format={check.format} mode={check.mode} size={check.size}")
        print(f"jfif_unit={check.info.get('jfif_unit')} density={check.info.get('jfif_density')}")
        print(
            f"sampling={JpegImagePlugin.get_sampling(check)} "
            f"qtables={len(check.quantization)}"
        )


if __name__ == "__main__":
    main()
