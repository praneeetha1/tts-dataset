import subprocess
import os
import imageio_ffmpeg
from sarvamai import SarvamAI

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
CHUNK_DURATION = 25  # seconds — under Sarvam's 30s limit

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")


def get_duration(wav_path):
    import re
    result = subprocess.run([FFMPEG, "-i", wav_path], capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        return 0.0
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def _split_wav(wav_path, chunk_dir, chunk_duration=CHUNK_DURATION):
    """Split wav into fixed-duration chunks for API calls. Returns list of chunk paths."""
    os.makedirs(chunk_dir, exist_ok=True)
    total = get_duration(wav_path)
    chunk_paths = []
    start = 0
    i = 0
    while start < total:
        chunk_path = os.path.join(chunk_dir, f"chunk_{i:03d}.wav")
        subprocess.run([
            FFMPEG, "-y", "-i", wav_path,
            "-ss", str(start), "-t", str(chunk_duration),
            "-ar", "24000", "-ac", "1", "-acodec", "pcm_s16le",
            chunk_path
        ], capture_output=True, check=True)
        chunk_paths.append(chunk_path)
        start += chunk_duration
        i += 1
    return chunk_paths


def transcribe_wav(wav_path, language_code="en-IN", client=None):
    """
    Transcribe a WAV file using Sarvam ASR.
    Automatically chunks if duration > 30s.
    Returns transcript string.
    """
    if client is None:
        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

    duration = get_duration(wav_path)

    if duration <= 28:
        # Single call
        with open(wav_path, "rb") as f:
            response = client.speech_to_text.transcribe(
                file=f,
                model="saaras:v3",
                mode="transcribe",
                language_code=language_code
            )
        return response.transcript if hasattr(response, "transcript") else str(response)

    # Chunk and stitch
    chunk_dir = wav_path.replace(".wav", "_chunks")
    chunk_paths = _split_wav(wav_path, chunk_dir)
    parts = []
    for chunk_path in chunk_paths:
        with open(chunk_path, "rb") as f:
            response = client.speech_to_text.transcribe(
                file=f,
                model="saaras:v3",
                mode="transcribe",
                language_code=language_code
            )
        text = response.transcript if hasattr(response, "transcript") else str(response)
        parts.append(text.strip())

    # Cleanup chunks
    for p in chunk_paths:
        os.remove(p)
    os.rmdir(chunk_dir)

    return " ".join(parts)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio.wav> [language_code]")
        sys.exit(1)

    wav = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "en-IN"
    print(f"Transcribing {wav} (lang={lang})...")
    transcript = transcribe_wav(wav, language_code=lang)
    print("\n--- TRANSCRIPT ---")
    print(transcript)
