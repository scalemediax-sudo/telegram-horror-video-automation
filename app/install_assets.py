"""Install private branding and narrator files into the persistent data directory."""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from . import media
from .config import DATA


def install_opening(source, destination):
    if media.duration(source) < 6:
        raise ValueError("The combined intro and disclaimer must be at least six seconds.")
    streams = media.probe(source)["streams"]
    if not any(stream["codec_type"] == "video" for stream in streams):
        raise ValueError("The intro and disclaimer must include video.")
    audio = any(stream["codec_type"] == "audio" for stream in streams)
    args = ["-i", source]
    if not audio:
        args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    media.ff(*args, "-map", "0:v:0", "-map", "0:a:0" if audio else "1:a:0",
             "-vf", "scale=1280:768:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                    "pad=1280:768:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24",
             "-af", "apad", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset", choices=("opening", "narrator"))
    parser.add_argument("source", help="File path, or - to read the file from stdin")
    args = parser.parse_args()
    target = (DATA / "branding" / "opening.mp4" if args.asset == "opening"
              else DATA / "_voice_refs" / "web-6-narrator-reference.wav")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as directory:
        if args.source == "-":
            source = Path(directory) / "input"
            with source.open("wb") as output:
                shutil.copyfileobj(sys.stdin.buffer, output)
        else:
            source = Path(args.source)
        output = Path(directory) / target.name
        if args.asset == "opening":
            install_opening(source, output)
        else:
            if not 6 <= media.duration(source) <= 30:
                raise ValueError("Use a narrator-only audio sample between 6 and 30 seconds.")
            media.ff("-i", source, "-map", "0:a:0", "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", output)
        output.replace(target)
    print(f"Installed {args.asset}.")


if __name__ == "__main__":
    main()
