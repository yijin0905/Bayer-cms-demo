#!/usr/bin/env python3
"""Animate the local Bayer KV and stream a seamless loop directly to FFmpeg."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "output/imagegen/bayer-kv-local-render-3840x1152.png"
DEFAULT_OUTPUT = ROOT / "output/imagegen/bayer-kv-video-3840x1152-10s.mp4"
DEFAULT_CONTACT = ROOT / "output/imagegen/bayer-kv-video-contact-sheet.jpg"

WIDTH = 3840
HEIGHT = 1152
WORK_SCALE = 0.5
WORK_W = int(WIDTH * WORK_SCALE)
WORK_H = int(HEIGHT * WORK_SCALE)
GREEN = np.array([154.0, 208.0, 76.0], dtype=np.float32) / 255.0
BLUE = np.array([80.0, 187.0, 249.0], dtype=np.float32) / 255.0
SEED = 1403155927


BLUE_POINTS = [
    (230, 856), (560, 811), (930, 716), (1280, 611), (1650, 645),
    (1920, 546), (2110, 421), (2030, 286), (1760, 216), (1450, 256),
    (1250, 406), (1330, 546), (1650, 645), (2040, 636), (2400, 526), (2725, 421),
]
GREEN_POINTS = [
    (245, 936), (600, 898), (970, 811), (1325, 711), (1650, 645),
    (1865, 571), (2075, 491), (2370, 451), (2720, 481),
]


def smoothstep(edge0: float, edge1: float, value: np.ndarray) -> np.ndarray:
    unit = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return unit * unit * (3.0 - 2.0 * unit)


def catmull_rom(points: list[tuple[float, float]], samples_per_segment: int = 260) -> np.ndarray:
    control = np.asarray(points, dtype=np.float64) * WORK_SCALE
    padded = np.vstack([control[0], control, control[-1]])
    chunks: list[np.ndarray] = []
    for index in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[index - 1 : index + 3]
        t = np.linspace(0.0, 1.0, samples_per_segment, endpoint=False)[:, None]
        curve = 0.5 * (
            2.0 * p1
            + (-p0 + p2) * t
            + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t**2
            + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t**3
        )
        chunks.append(curve)
    chunks.append(control[-1][None, :])
    return np.vstack(chunks)


def arc_length_path(points: list[tuple[float, float]], count: int = 8192) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dense = catmull_rom(points)
    lengths = np.linalg.norm(np.diff(dense, axis=0), axis=1)
    cumulative = np.r_[0.0, np.cumsum(lengths)]
    target = np.linspace(0.0, cumulative[-1], count)
    x = np.interp(target, cumulative, dense[:, 0])
    y = np.interp(target, cumulative, dense[:, 1])
    path = np.column_stack([x, y]).astype(np.float32)
    tangent = np.gradient(path, axis=0)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-6)
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]]).astype(np.float32)
    return path, tangent.astype(np.float32), normal


def deposit_bilinear(field: np.ndarray, x: np.ndarray, y: np.ndarray, amount: np.ndarray) -> None:
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    fx = x - x0
    fy = y - y0
    for dx, dy, share in (
        (0, 0, (1.0 - fx) * (1.0 - fy)),
        (1, 0, fx * (1.0 - fy)),
        (0, 1, (1.0 - fx) * fy),
        (1, 1, fx * fy),
    ):
        xx = x0 + dx
        yy = y0 + dy
        valid = (xx >= 0) & (xx < WORK_W) & (yy >= 0) & (yy < WORK_H)
        np.add.at(field, (yy[valid], xx[valid]), (amount * share)[valid])


def blur(field: np.ndarray, radius: float, scale: float = 1.0) -> np.ndarray:
    encoded = np.clip(field * scale * 255.0, 0.0, 255.0).astype(np.uint8)
    image = Image.fromarray(encoded, "L").filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(image, dtype=np.float32) / (255.0 * scale)


class MovingStream:
    def __init__(
        self,
        rng: np.random.Generator,
        points: list[tuple[float, float]],
        color: np.ndarray,
        particle_count: int,
        energy: float,
        width_scale: float,
    ) -> None:
        self.path, self.tangent, self.normal = arc_length_path(points)
        self.color = color
        self.energy = energy
        self.u0 = rng.random(particle_count).astype(np.float32)
        self.speed = rng.choice(np.array([1.0, 1.0, 1.0, 2.0], dtype=np.float32), particle_count)
        selector = rng.random(particle_count)
        self.offset = np.where(
            selector < 0.76,
            rng.normal(0.0, 0.25, particle_count),
            np.where(selector < 0.97, rng.normal(0.0, 0.62, particle_count), rng.normal(0.0, 1.15, particle_count)),
        ).astype(np.float32)
        self.alpha = (0.075 + 0.42 * rng.random(particle_count) ** 2.2).astype(np.float32)
        self.drift_phase = rng.uniform(0.0, math.tau, particle_count).astype(np.float32)
        self.drift_harmonic = rng.choice(np.array([1.0, 2.0, 3.0], dtype=np.float32), particle_count)
        u = np.linspace(0.0, 1.0, len(self.path), dtype=np.float32)
        width = (
            9.0
            + 27.0 * np.maximum(np.sin(np.pi * u), 0.0) ** 1.25
            + 17.0 * np.exp(-0.5 * ((u - 0.52) / 0.22) ** 2)
            + 5.0 * np.sin(math.tau * (1.18 * u + 0.17))
        )
        self.width = np.maximum(width * width_scale, 7.0).astype(np.float32)
        self.filaments = self._make_filaments(rng)

    def _make_filaments(self, rng: np.random.Generator) -> list[np.ndarray]:
        groups: list[np.ndarray] = []
        u = np.linspace(0.0, 1.0, len(self.path), dtype=np.float32)
        for group in range(4):
            image = Image.new("L", (WORK_W, WORK_H), 0)
            draw = ImageDraw.Draw(image)
            for _ in range(5):
                base = rng.normal(0.0, 0.30 + group * 0.12)
                phase = rng.uniform(0.0, math.tau)
                offset = base + rng.uniform(0.02, 0.08) * np.sin(math.tau * rng.uniform(0.8, 2.0) * u + phase)
                shifted = self.path + self.normal * (self.width * offset)[:, None]
                begin = int(rng.uniform(0.04, 0.13) * len(shifted))
                end = int(rng.uniform(0.82, 0.96) * len(shifted))
                coords = [tuple(map(float, point)) for point in shifted[begin:end:9]]
                draw.line(coords, fill=int(rng.uniform(20, 46)), width=1, joint="curve")
            groups.append(np.asarray(image.filter(ImageFilter.GaussianBlur(0.55)), dtype=np.float32) / 255.0)
        return groups

    def render(self, phase: float) -> np.ndarray:
        u = np.mod(self.u0 + phase * self.speed, 1.0)
        index = np.minimum((u * (len(self.path) - 1)).astype(np.int32), len(self.path) - 1)
        drift = 1.0 + 0.075 * np.sin(math.tau * phase * self.drift_harmonic + self.drift_phase)
        offset = self.offset * self.width[index] * drift
        xy = self.path[index] + self.normal[index] * offset[:, None]

        taper = np.maximum(np.sin(np.pi * u), 0.0) ** 0.68
        pulse = 0.64 + 0.36 * (0.5 + 0.5 * np.cos(math.tau * (5.0 * u - 2.0 * phase) + self.drift_phase * 0.22))
        amount = self.alpha * taper * pulse * self.energy
        sharp = np.zeros((WORK_H, WORK_W), dtype=np.float32)
        deposit_bilinear(sharp, xy[:, 0], xy[:, 1], amount)

        # Short tangent-aligned afterimages make motion legible without thick tubes.
        for lag, gain in ((1.6, 0.28), (3.4, 0.12)):
            lagged = xy - self.tangent[index] * lag
            deposit_bilinear(sharp, lagged[:, 0], lagged[:, 1], amount * gain)

        light = sharp * 1.18
        light += blur(sharp, 1.15, 1.2) * 0.68
        light += blur(sharp, 4.8, 2.2) * 1.05
        for group, mask in enumerate(self.filaments):
            shimmer = 0.035 + 0.025 * math.sin(math.tau * ((group % 3 + 1) * phase) + group * 1.37)
            light += mask * shimmer
        return light[:, :, None] * self.color[None, None, :]


def make_safety_mask() -> np.ndarray:
    yy, xx = np.mgrid[0:WORK_H, 0:WORK_W].astype(np.float32)
    right = 1.0 - smoothstep(1230.0, 1395.0, xx)
    vertical = smoothstep(10.0, 34.0, yy) * (1.0 - smoothstep(WORK_H - 34.0, WORK_H - 10.0, yy))
    logo_x = 1.0 - smoothstep(300.0, 390.0, xx)
    logo_y = 1.0 - smoothstep(115.0, 185.0, yy)
    logo_guard = 1.0 - logo_x * logo_y
    return (right * vertical * logo_guard).astype(np.float32)


def make_center_glow() -> np.ndarray:
    yy, xx = np.mgrid[0:WORK_H, 0:WORK_W].astype(np.float32)
    cx = 1650.0 * WORK_SCALE
    cy = 645.0 * WORK_SCALE
    core = np.exp(-0.5 * (((xx - cx) / 42.0) ** 2 + ((yy - cy) / 24.0) ** 2))
    halo = np.exp(-0.5 * (((xx - cx) / 105.0) ** 2 + ((yy - cy) / 55.0) ** 2))
    return (core * 0.75 + halo * 0.25).astype(np.float32)


def locate_ffmpeg() -> str:
    direct = shutil.which("ffmpeg")
    if direct:
        return direct
    try:
        import imageio_ffmpeg
    except ImportError:
        # The project venv may hold only the portable FFmpeg package while this
        # script runs with Codex's bundled numpy/Pillow runtime.
        venv_site = ROOT / ".venv/lib/python3.12/site-packages"
        if venv_site.exists():
            sys.path.insert(0, str(venv_site))
        try:
            import imageio_ffmpeg
        except ImportError as exc:
            raise RuntimeError("FFmpeg not found. Install imageio-ffmpeg in the project venv.") from exc
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except RuntimeError as exc:
        raise RuntimeError("imageio-ffmpeg is installed but its FFmpeg binary is unavailable.") from exc


def encoder_args(ffmpeg: str, output: Path, fps: int, frame_count: int, preset: str, crf: int) -> list[str]:
    encoders = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).stdout
    if "libx264" in encoders:
        codec_args = [
            "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-profile:v", "high", "-level:v", "5.1",
            "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709:fullrange=off",
        ]
    elif "h264_videotoolbox" in encoders:
        codec_args = ["-c:v", "h264_videotoolbox", "-b:v", "28M", "-maxrate", "36M", "-bufsize", "56M", "-profile:v", "high"]
    else:
        raise RuntimeError("The available FFmpeg has neither libx264 nor h264_videotoolbox.")
    return [
        ffmpeg, "-hide_banner", "-loglevel", "warning", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s:v", f"{WIDTH}x{HEIGHT}", "-framerate", str(fps), "-i", "pipe:0",
        "-frames:v", str(frame_count), "-an",
        "-vf", "scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=bicubic+accurate_rnd,format=yuv420p",
        *codec_args,
        "-fps_mode", "cfr", "-color_range", "tv", "-colorspace", "bt709",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-tag:v", "avc1",
        "-movflags", "+faststart", "-y", str(output),
    ]


def render_video(args: argparse.Namespace, ffmpeg: str) -> float:
    base = Image.open(args.base).convert("RGB")
    if base.size != (WIDTH, HEIGHT):
        raise ValueError(f"Base image must be {WIDTH}x{HEIGHT}; got {base.size[0]}x{base.size[1]}.")
    frame_count = int(round(args.duration * args.fps))
    rng = np.random.default_rng(SEED)
    blue = MovingStream(rng, BLUE_POINTS, BLUE, particle_count=7300, energy=0.82, width_scale=0.92)
    green = MovingStream(rng, GREEN_POINTS, GREEN, particle_count=7600, energy=1.08, width_scale=1.08)
    safety = make_safety_mask()
    center = make_center_glow()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = encoder_args(ffmpeg, args.output, args.fps, frame_count, args.preset, args.crf)
    started = time.perf_counter()
    with tempfile.TemporaryFile(mode="w+b") as ffmpeg_log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=ffmpeg_log)
        assert process.stdin is not None
        try:
            for frame_index in range(frame_count):
                phase = frame_index / frame_count
                dynamic = blue.render(phase) + green.render(phase)
                breath = 0.022 + 0.025 * (0.5 + 0.5 * math.sin(math.tau * (2.0 * phase - 0.25)))
                center_color = np.array([0.58, 0.90, 0.78], dtype=np.float32)
                dynamic += center[:, :, None] * center_color[None, None, :] * breath
                dynamic *= safety[:, :, None]
                dynamic = np.clip(dynamic, 0.0, 0.34)
                overlay_small = Image.fromarray((dynamic * 255.0 + 0.5).astype(np.uint8), "RGB")
                overlay = overlay_small.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
                frame = ImageChops.screen(base, overlay)
                process.stdin.write(frame.tobytes())
                if frame_index == 0 or (frame_index + 1) % args.fps == 0:
                    elapsed = time.perf_counter() - started
                    print(f"Rendered {frame_index + 1}/{frame_count} frames ({elapsed:.1f}s)", flush=True)
        except BrokenPipeError as exc:
            ffmpeg_log.seek(0)
            details = ffmpeg_log.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"FFmpeg closed the raw-video pipe early:\n{details}") from exc
        finally:
            process.stdin.close()
        return_code = process.wait()
        if return_code != 0:
            ffmpeg_log.seek(0)
            details = ffmpeg_log.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"FFmpeg exited with status {return_code}:\n{details}")
    return time.perf_counter() - started


def probe_video(path: Path, ffmpeg: str) -> dict[str, object]:
    ffprobe = shutil.which("ffprobe")
    sibling = Path(ffmpeg).with_name("ffprobe")
    if not ffprobe and sibling.exists():
        ffprobe = str(sibling)
    if ffprobe:
        result = subprocess.run(
            [
                ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                "stream=codec_name,width,height,pix_fmt,r_frame_rate,avg_frame_rate,color_range,color_space,color_transfer,color_primaries,nb_frames:format=duration",
                "-of", "json", str(path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        metadata = json.loads(result.stdout)
        metadata["probe"] = "ffprobe"
        return metadata

    import imageio_ffmpeg

    reader = imageio_ffmpeg.read_frames(str(path), pix_fmt="rgb24")
    metadata = next(reader)
    reader.close()
    frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(path))
    return {
        "probe": "imageio_ffmpeg fallback",
        "codec": metadata.get("codec"),
        "size": metadata.get("size"),
        "fps": metadata.get("fps"),
        "duration": seconds,
        "frames": frames,
    }


def create_contact_sheet(path: Path, destination: Path, ffmpeg: str, frame_count: int) -> None:
    picks = np.linspace(0, frame_count - 1, 6).round().astype(int).tolist()
    select = "+".join(f"eq(n\\,{number})" for number in picks)
    filters = f"select={select},scale=960:288:flags=lanczos,tile=3x2:padding=12:margin=12:color=0x080d0a"
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg, "-hide_banner", "-loglevel", "warning", "-i", str(path),
            "-vf", filters, "-frames:v", "1", "-q:v", "2", "-update", "1", "-y", str(destination),
        ],
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--contact-sheet", type=Path, default=DEFAULT_CONTACT)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--preset", default="medium")
    parser.add_argument("--crf", type=int, default=18)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.duration <= 0.0 or args.fps <= 0:
        raise ValueError("Duration and FPS must be positive.")
    ffmpeg = locate_ffmpeg()
    print(f"Using FFmpeg: {ffmpeg}")
    elapsed = render_video(args, ffmpeg)
    frame_count = int(round(args.duration * args.fps))
    metadata = probe_video(args.output, ffmpeg)
    create_contact_sheet(args.output, args.contact_sheet, ffmpeg, frame_count)
    print(f"Saved video: {args.output}")
    print(f"Saved contact sheet: {args.contact_sheet}")
    print(f"Encoding verification: {json.dumps(metadata, ensure_ascii=True)}")
    print(f"Total render + encode time: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
