#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video SVD compression pipeline simulator (grayscale, low-rank SVD factors on disk).

Sample requirements.txt (install with: pip install -r requirements.txt):
    numpy>=1.20
    opencv-python>=4.5
    tqdm>=4.60
"""

import argparse
import json
import os

import cv2
import numpy as np
from tqdm import tqdm


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Simulate video 'compression' via per-frame SVD truncation on normalized "
            "grayscale frames: extract → factorize → save .npy → load → reconstruct video."
        )
    )
    p.add_argument("--input", required=True, help="Path to input video file.")
    p.add_argument("--output", required=True, help="Path for reconstructed output video.")
    p.add_argument(
        "--factors_dir",
        default="./compressed_factors",
        help="Directory to store/load U, S, Vt .npy files per frame.",
    )
    p.add_argument(
        "--keep_ratio",
        type=float,
        default=0.1,
        help="Fraction of singular values to keep (default: 0.1 = 10%%).",
    )
    return p.parse_args()


def open_video_capture(path):
    """Open cv2.VideoCapture with basic validation."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Input video not found: {path}")
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open video (invalid or unsupported format): {path}")
    return cap


def write_metadata(factors_dir, fps, width, height, frame_count):
    meta = {
        "fps": float(fps),
        "width": int(width),
        "height": int(height),
        "frame_count": int(frame_count),
    }
    path = os.path.join(factors_dir, "metadata.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def read_metadata(factors_dir):
    path = os.path.join(factors_dir, "metadata.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing metadata.json in factors directory: {factors_dir}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def frame_index_from_basename(basename):
    """Extract integer frame index from 'frame_000042_U.npy' style name."""
    if not basename.endswith("_U.npy"):
        return None
    stem = basename[: -len("_U.npy")]
    if not stem.startswith("frame_"):
        return None
    num = stem[len("frame_") :]
    if not num.isdigit():
        return None
    return int(num)


def list_frame_indices_from_factors(factors_dir):
    """Return sorted list of frame indices that have U/S/Vt triplets."""
    if not os.path.isdir(factors_dir):
        raise FileNotFoundError(f"Factors directory not found: {factors_dir}")
    u_files = [f for f in os.listdir(factors_dir) if f.endswith("_U.npy")]
    indices = []
    for name in u_files:
        idx = frame_index_from_basename(name)
        if idx is None:
            continue
        base = f"frame_{idx:06d}"
        s_path = os.path.join(factors_dir, f"{base}_S.npy")
        vt_path = os.path.join(factors_dir, f"{base}_Vt.npy")
        if os.path.isfile(s_path) and os.path.isfile(vt_path):
            indices.append(idx)
    indices.sort()
    if not indices:
        raise RuntimeError(
            f"No complete U/S/Vt frame triplets found under {factors_dir}"
        )
    return indices


def compress_phase(args):
    """
    Extract frames, convert to normalized grayscale, SVD, truncate, save factors.

    Normalization: pixel values are divided by 255 so each entry lies in [0, 1].
    This stabilizes the scale of the matrix before SVD: singular values reflect
    energy in a comparable range across frames and avoid numerical issues from
    raw 0–255 uint8 dynamics when interpreting truncation as low-rank approximation.
    """
    cap = open_video_capture(args.input)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    os.makedirs(args.factors_dir, exist_ok=True)
    keep_ratio = float(args.keep_ratio)
    if keep_ratio <= 0 or keep_ratio > 1:
        cap.release()
        raise ValueError("--keep_ratio must be in (0, 1].")

    frame_idx = 0
    pbar = tqdm(desc="Compression (SVD + save factors)", unit="frame", dynamic_ncols=True)

    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            break

        # Single-channel grayscale, then float32 for linear algebra
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        frame_f = gray.astype(np.float32)
        # Map brightness to [0, 1] for SVD on a well-scaled matrix
        frame_normalized = frame_f / 255.0

        U, S, Vt = np.linalg.svd(frame_normalized, full_matrices=False)
        k = int(len(S) * keep_ratio)
        U_trunc = U[:, :k]
        S_trunc = S[:k]
        Vt_trunc = Vt[:k, :]

        base = os.path.join(args.factors_dir, f"frame_{frame_idx:06d}")
        np.save(f"{base}_U.npy", U_trunc)
        np.save(f"{base}_S.npy", S_trunc)
        np.save(f"{base}_Vt.npy", Vt_trunc)

        frame_idx += 1
        pbar.update(1)

    pbar.close()
    cap.release()

    if frame_idx == 0:
        raise RuntimeError("No frames read from input video (empty or unreadable stream).")

    write_metadata(args.factors_dir, fps, width, height, frame_idx)
    print(
        f"Compression done: {frame_idx} frames → factors in {args.factors_dir!r} "
        f"({width}x{height} @ {fps} fps)."
    )


def reconstruct_phase(args):
    """Load reduced factors, reconstruct each frame, write output video."""
    meta = read_metadata(args.factors_dir)
    fps = meta["fps"]
    width = meta["width"]
    height = meta["height"]
    expected_count = meta["frame_count"]

    indices = list_frame_indices_from_factors(args.factors_dir)
    if len(indices) != expected_count:
        print(
            f"Warning: metadata frame_count={expected_count} but found "
            f"{len(indices)} complete triplets on disk."
        )

    out_dir = os.path.dirname(os.path.abspath(args.output))
    if out_dir and not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"Cannot create output directory: {out_dir}") from e

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(args.output, fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(
            f"Could not open VideoWriter for {args.output!r} "
            f"(check path, codec support, and resolution)."
        )

    try:
        for idx in tqdm(indices, desc="Reconstruction (load + write video)", unit="frame", dynamic_ncols=True):
            base = os.path.join(args.factors_dir, f"frame_{idx:06d}")
            u_path = f"{base}_U.npy"
            s_path = f"{base}_S.npy"
            vt_path = f"{base}_Vt.npy"
            for p in (u_path, s_path, vt_path):
                if not os.path.isfile(p):
                    raise FileNotFoundError(f"Missing factor file: {p}")

            U_trunc = np.load(u_path)
            S_trunc = np.load(s_path)
            Vt_trunc = np.load(vt_path)

            recon = U_trunc @ np.diag(S_trunc) @ Vt_trunc
            recon = np.clip(recon * 255.0, 0, 255).astype(np.uint8)
            # BGR 3-channel: repeat grayscale so VideoWriter gets expected shape
            bgr = cv2.cvtColor(recon, cv2.COLOR_GRAY2BGR)
            writer.write(bgr)
    finally:
        writer.release()

    print(f"Reconstruction written: {args.output!r} ({width}x{height} @ {fps} fps).")


def main():
    args = parse_args()
    try:
        compress_phase(args)
        reconstruct_phase(args)
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"Error: {e}")
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
