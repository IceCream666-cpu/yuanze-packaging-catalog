"""Render an original, seamless orange/pink glow loop for the login preview.

Run with the repository's .venv Python (numpy, Pillow, imageio-ffmpeg).
The reference screenshot is not composited into the result.
"""
from pathlib import Path
import hashlib
import json
import math
import subprocess

import imageio_ffmpeg
import numpy as np
from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / "assets"
WIDTH, HEIGHT, FPS, SECONDS = 576, 768, 24, 10
Y, X = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32) / WIDTH
GRAIN = np.random.default_rng(42).uniform(-0.65, 0.65, (HEIGHT, WIDTH, 1)).astype(np.float32)


def blend(canvas, color, alpha):
    weight = np.clip(alpha, 0, 1)[..., None]
    return canvas * (1 - weight) + np.array(color, dtype=np.float32) * weight


def frame(seconds):
    phase = 2 * math.pi * (seconds % SECONDS) / SECONDS
    canvas = np.empty((HEIGHT, WIDTH, 3), dtype=np.float32)
    canvas[:] = (255, 109, 12)
    # Soft, drifting ambient pools give the orange surface depth.
    canvas = blend(canvas, (255, 220, 177), .72 * np.exp(
        -(((X - .31 - .1 * math.sin(phase)) / .65) ** 2 + ((Y - .64 - .08 * math.cos(phase)) / .65) ** 2)))
    canvas = blend(canvas, (255, 64, 137), .7 * np.exp(
        -(((X - 1.03) / .33) ** 2 + ((Y + .03) / .23) ** 2)))
    canvas = blend(canvas, (255, 66, 145), .58 * np.exp(
        -(((X + .04) / .34) ** 2 + ((Y - 1.34) / .3) ** 2)))
    canvas = blend(canvas, (255, 169, 82), .3 * np.exp(
        -(((X - .88) / .52) ** 2 + ((Y - 1.15) / .44) ** 2)))

    orbs = [
        (.27 + .10 * math.sin(phase), .60 + .14 * math.cos(phase), .218 + .03 * math.sin(phase + .5), (255, 138, 193), phase),
        (.74 + .10 * math.sin(phase + 1.4), .77 + .15 * math.cos(phase + 1.4), .228 + .03 * math.cos(phase), (255, 129, 181), phase + 1.4),
    ]
    for cx, cy, radius, color, orbit in orbs:
        # A slow elliptical stretch makes the light feel fluid as it drifts.
        # All motion is encoded here; the page only decodes the small MP4.
        stretch = 1 + .12 * math.sin(orbit)
        distance = np.sqrt(((X - cx) / stretch) ** 2 + ((Y - cy) * stretch) ** 2)
        canvas = blend(canvas, (255, 225, 163), .34 * np.exp(-(distance / (radius * 1.65)) ** 2))
        # Wide soft halo, with a pink center; no hard circle boundary.
        halo = (.75 + .08 * math.cos(orbit)) * np.exp(-((distance - radius) / (radius * .24)) ** 2)
        canvas = blend(canvas, (255, 244, 201), halo)
        core = .94 * np.exp(-(distance / (radius * .89)) ** 4)
        canvas = blend(canvas, color, core)
        canvas = blend(canvas, (255, 188, 211), .25 * np.exp(
            -(((X - cx + radius * .12) / (radius * .7)) ** 2 + ((Y - cy + radius * .32) / (radius * .65)) ** 2)))
    return np.clip(canvas + GRAIN, 0, 255).astype(np.uint8)


def build():
    ASSETS.mkdir(parents=True, exist_ok=True)
    poster = ASSETS / "login-glow-poster.jpg"
    video = ASSETS / "login-glow.mp4"
    first = frame(0)
    assert np.array_equal(first, frame(SECONDS)), "Animation must close without a seam"
    motion_delta = float(np.abs(first.astype(np.float32) - frame(SECONDS / 4)).mean())
    assert motion_delta > 8, "The floating light should visibly move, not resemble a still image"
    seam_delta = float(np.abs(first.astype(np.float32) - frame(SECONDS - 1 / FPS)).mean())
    assert seam_delta < 2, "The final encoded frame should approach the first smoothly"
    Image.fromarray(first).save(poster, quality=94, optimize=True)
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
        "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(video),
    ]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
        for index in range(FPS * SECONDS):
            process.stdin.write(frame(index / FPS).tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("Glow video encoding failed")
    # Decode the whole clip, rather than trusting container metadata.
    subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-xerror",
        "-i", str(video), "-f", "null", "-",
    ], check=True)
    manifest = {
        "source": "Original procedural orange/pink glow animation based on the requested visual direction",
        "generator": "scripts/build-glow.py",
        "width": WIDTH, "height": HEIGHT, "fps": FPS, "durationSeconds": SECONDS,
        "codec": "H.264 / yuv420p", "fastStart": True, "audio": False,
        "loopBoundaryPixelsEqual": True, "fullDecode": "passed",
        "motion": {"quarterLoopMeanPixelDelta": round(motion_delta, 3), "lastToFirstMeanPixelDelta": round(seam_delta, 3)},
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in [video, poster]},
    }
    (ASSETS / "glow-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    build()
