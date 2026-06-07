"""
TTS Dataset Pipeline
Usage:
    python pipeline.py --url <youtube_url> --lang en-IN --source nptel --start 00:01:10 --end 00:10:00
    python pipeline.py --url <youtube_url> --lang hi-IN --source podcast
"""
import argparse
import subprocess
import os
import json
import re
import shutil
from sarvamai import SarvamAI

from segment import segment_audio
from transcribe import transcribe_wav
from tag_emotion import tag_emotion

FFMPEG = shutil.which("ffmpeg") or os.path.expanduser("~/.local/bin/ffmpeg")
import shutil
YTDLP = shutil.which("yt-dlp") or os.path.expanduser("~/Library/Python/3.11/bin/yt-dlp")
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
if not SARVAM_API_KEY:
    raise EnvironmentError("SARVAM_API_KEY env var not set")

DATASET_DIR = "dataset"
AUDIO_DIR = os.path.join(DATASET_DIR, "audio")
METADATA_FILE = os.path.join(DATASET_DIR, "metadata.jsonl")
REJECTED_DIR = os.path.join(DATASET_DIR, "rejected")
REJECTED_METADATA_FILE = os.path.join(DATASET_DIR, "rejected_metadata.jsonl")


def extract_video_id(url):
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else url.split("/")[-1][:11]


def download_audio(url, out_path):
    print(f"Downloading audio: {url}")
    deno_path = shutil.which("deno") or os.path.expanduser("~/.deno/bin/deno")
    cookies_file = os.path.expanduser("~/.yt-cookies.txt")
    cmd = [
        YTDLP,
        "--ffmpeg-location", os.path.dirname(FFMPEG),
        "--js-runtimes", f"deno:{deno_path}",
        "--force-overwrites",
        "-x", "-o", out_path,
    ]
    if os.path.exists(cookies_file):
        cmd += ["--cookies", cookies_file]
    else:
        cmd += ["--cookies-from-browser", "chrome"]
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed:\n{result.stderr[-500:]}")
    downloaded = next(
        (f for f in os.listdir(".") if f.startswith(os.path.splitext(out_path)[0])),
        None
    )
    return downloaded


def convert_to_wav(input_path, output_path, start=None, end=None):
    """Convert to 24kHz mono WAV, optionally trimming to [start, end]."""
    cmd = [FFMPEG, "-y", "-i", input_path]
    if start:
        cmd += ["-ss", start]
    if end:
        cmd += ["-to", end]
    cmd += ["-ar", "24000", "-ac", "1", "-acodec", "pcm_s16le", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg convert failed:\n{result.stderr[-500:]}")


def get_snr(wav_path):
    """Estimate SNR using ffmpeg volumedetect. Returns mean_volume in dB (less negative = louder/cleaner)."""
    result = subprocess.run([
        FFMPEG, "-i", wav_path, "-af", "volumedetect", "-f", "null", "-"
    ], capture_output=True, text=True)
    match = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", result.stderr)
    return float(match.group(1)) if match else None


def quality_ok(seg_info, transcript, wav_path=None):
    dur = seg_info["duration_seconds"]
    if dur < 10 or dur > 28:
        return False, f"duration {dur:.1f}s out of range"
    if len(transcript.strip()) < 20:
        return False, "transcript too short"
    if len(transcript) > 600:
        return False, "transcript suspiciously long (possible hallucination)"

    # Word-duration check: catches ASR mismatches / hallucinations
    word_count = len(transcript.strip().split())
    if word_count > 0 and (dur / word_count) > 0.8:
        return False, f"word duration too high ({dur/word_count:.2f}s/word — likely ASR mismatch)"

    # SNR check: catches noisy/silent segments
    if wav_path:
        snr = get_snr(wav_path)
        if snr is not None and snr < -35:
            return False, f"SNR too low ({snr:.1f}dB — likely noise or silence)"

    return True, ""


def run(url, lang, source_type, start=None, end=None, local_file=None):
    os.makedirs(AUDIO_DIR, exist_ok=True)

    video_id = extract_video_id(url)
    filename_prefix = f"{lang}_{source_type}_{video_id}"

    # Step 1: Download (or use local file)
    if local_file:
        downloaded = local_file
        print(f"Using local file: {downloaded}")
    else:
        raw_path = f"_raw_{video_id}"
        downloaded = download_audio(url, raw_path)
        if not downloaded:
            raise RuntimeError("Download failed — no file found")
        print(f"Downloaded: {downloaded}")

    # Step 2: Convert + optional trim
    full_wav = f"_full_{video_id}.wav"
    convert_to_wav(downloaded, full_wav, start=start, end=end)
    print(f"Converted to WAV: {full_wav}")

    # Step 3: Segment
    print("\nSegmenting...")
    os.makedirs(REJECTED_DIR, exist_ok=True)
    segments = segment_audio(full_wav, AUDIO_DIR, filename_prefix)

    # Step 4: Transcribe + tag each segment
    client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
    written = 0
    skipped = 0

    print(f"\nTranscribing and tagging {len(segments)} segments...")
    for seg in segments:
        seg_path = os.path.join(AUDIO_DIR, seg["file"])

        transcript = transcribe_wav(seg_path, language_code=lang, client=client)
        ok, reason = quality_ok(seg, transcript, wav_path=seg_path)
        if not ok:
            print(f"  SKIP {seg['file']}: {reason}")
            rejected_path = os.path.join(REJECTED_DIR, seg["file"])
            os.rename(seg_path, rejected_path)
            rejected_row = {
                "file": seg["file"],
                "transcript": transcript.strip(),
                "language": lang,
                "source_type": source_type,
                "duration_seconds": seg["duration_seconds"],
                "source_video": video_id,
                "rejection_reason": reason,
                "sample_rate": 24000
            }
            with open(REJECTED_METADATA_FILE, "a") as f:
                f.write(json.dumps(rejected_row, ensure_ascii=False) + "\n")
            skipped += 1
            continue

        emotion = tag_emotion(transcript, client=client)

        row = {
            "file": seg["file"],
            "transcript": transcript.strip(),
            "language": lang,
            "source_type": source_type,
            "emotion": emotion,
            "duration_seconds": seg["duration_seconds"],
            "source_video": video_id,
            "sample_rate": 24000
        }

        with open(METADATA_FILE, "a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

        print(f"  OK  {seg['file']} | {emotion} | {seg['duration_seconds']:.1f}s")
        written += 1

    # Cleanup — only delete the download if it was fetched by yt-dlp, not a local file the user provided
    if not local_file:
        os.remove(downloaded)
    os.remove(full_wav)

    print(f"\nDone. {written} segments written, {skipped} skipped.")
    print(f"Metadata: {METADATA_FILE}")
    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--lang", default="en-IN", help="e.g. en-IN, hi-IN")
    parser.add_argument("--source", required=True, help="e.g. nptel, podcast, standup")
    parser.add_argument("--start", default=None, help="Trim start e.g. 00:01:10")
    parser.add_argument("--end", default=None, help="Trim end e.g. 00:10:00")
    args = parser.parse_args()

    run(args.url, args.lang, args.source, start=args.start, end=args.end)
