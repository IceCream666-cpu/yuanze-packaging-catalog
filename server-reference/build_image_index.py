#!/usr/bin/env python3
"""Run after changing catalog, media, model or preprocessing; no network is used."""
import argparse
import json
from pathlib import Path
from image_search import build_index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the private packaging image similarity index")
    parser.add_argument("--private", type=Path, default=Path(__file__).resolve().parent / "private")
    args = parser.parse_args()

    def progress(done, total, indexed):
        if done == 1 or done % 20 == 0 or done == total:
            print(f"Images processed: {done}/{total}; indexed: {indexed}", flush=True)

    print(json.dumps(build_index(args.private, progress), ensure_ascii=False), flush=True)
