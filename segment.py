import subprocess
import re
import os
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

TARGET_DURATION = 25   # seconds — Sarvam ASR limit is 30s
MIN_DURATION = 10
MAX_DURATION = 28


def get_audio_duration(wav_path):
    result = subprocess.run(
        [FFMPEG, "-i", wav_path],
        capture_output=True, text=True
    )
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        raise ValueError(f"Could not determine duration of {wav_path}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def detect_silences(wav_path, noise_db=-30, min_duration=0.4):
    """Run ffmpeg silencedetect and return list of silence midpoint timestamps."""
    result = subprocess.run([
        FFMPEG, "-i", wav_path,
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null", "-"
    ], capture_output=True, text=True)

    starts = re.findall(r"silence_start: ([\d.]+)", result.stderr)
    ends = re.findall(r"silence_end: ([\d.]+)", result.stderr)

    midpoints = []
    for s, e in zip(starts, ends):
        midpoints.append((float(s) + float(e)) / 2)

    return midpoints


def compute_segments(total_duration, silence_midpoints,
                     target=TARGET_DURATION, min_dur=MIN_DURATION, max_dur=MAX_DURATION):
    """Greedy segmenter: snap cuts to nearest silence near the target mark."""
    segments = []
    start = 0.0

    while start < total_duration - min_dur:
        ideal_end = start + target
        window_min = start + min_dur
        window_max = min(start + max_dur, total_duration)

        candidates = [t for t in silence_midpoints if window_min < t < window_max]

        if candidates:
            end = min(candidates, key=lambda t: abs(t - ideal_end))
        else:
            # No silence found — force cut at target or end of audio
            end = min(ideal_end, total_duration)

        segments.append((round(start, 3), round(end, 3)))
        start = end

    return segments


def extract_segment(wav_path, start, end, out_path):
    """Cut a segment from wav_path and write to out_path as 16kHz mono WAV."""
    duration = end - start
    subprocess.run([
        FFMPEG, "-y",
        "-i", wav_path,
        "-ss", str(start),
        "-t", str(duration),
        "-ar", "24000",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        out_path
    ], capture_output=True, check=True)


def segment_audio(wav_path, out_dir, filename_prefix):
    """
    Full segmentation pipeline for one WAV file.
    Returns list of dicts: {file, start, end, duration}
    """
    os.makedirs(out_dir, exist_ok=True)

    total = get_audio_duration(wav_path)
    print(f"Audio duration: {total:.1f}s")

    silences = detect_silences(wav_path)
    print(f"Found {len(silences)} silence points")

    segments = compute_segments(total, silences)
    print(f"Generated {len(segments)} segments")

    results = []
    for i, (start, end) in enumerate(segments):
        duration = end - start
        filename = f"{filename_prefix}_{i+1:03d}.wav"
        out_path = os.path.join(out_dir, filename)
        extract_segment(wav_path, start, end, out_path)
        results.append({
            "file": filename,
            "start": start,
            "end": end,
            "duration_seconds": round(duration, 3)
        })
        print(f"  [{i+1:03d}] {start:.1f}s → {end:.1f}s ({duration:.1f}s) → {filename}")

    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python segment.py <input.wav> <out_dir> <filename_prefix>")
        sys.exit(1)

    wav_path, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    results = segment_audio(wav_path, out_dir, prefix)
    print(f"\nDone. {len(results)} segments written to {out_dir}/")
