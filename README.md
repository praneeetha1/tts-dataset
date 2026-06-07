# TTS Dataset Pipeline

A pipeline for building high-quality Text-to-Speech (TTS) datasets from Indian-language audio/video sources. It downloads audio from YouTube, segments it at natural speech boundaries, transcribes each segment using Sarvam AI's ASR, tags it with a speaking-style/emotion label, and exports a JSONL metadata file ready for HuggingFace upload.

## Supported Languages

`en-IN`, `hi-IN`, `te-IN`, and any other language code accepted by Sarvam AI's `saaras:v3` model.

## Pipeline Overview

```
YouTube URL / local file
        │
        ▼
   download_audio          yt-dlp
        │
        ▼
   convert_to_wav          ffmpeg → 24kHz mono WAV (optional trim)
        │
        ▼
   segment_audio           silence-detect → 10–28s segments
        │
        ▼
   transcribe_wav          Sarvam ASR (saaras:v3)
        │
        ▼
   quality_ok              duration / word-rate / SNR checks
        │
        ├── FAIL → dataset/rejected/
        │
        ▼
   tag_emotion             Sarvam LLM (sarvam-30b)
        │
        ▼
   dataset/metadata.jsonl
```

## Setup

### Requirements

- Python 3.11+
- `ffmpeg` (system install or `~/.local/bin/ffmpeg`)
- `yt-dlp`
- `deno` (used by yt-dlp for JS runtimes)

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install sarvamai imageio-ffmpeg datasets huggingface_hub
```

### Environment variables

Create a `.env` file or export before running:

```bash
export SARVAM_API_KEY=your_key_here
```

## Usage

### Run the full pipeline

```bash
python pipeline.py --url <youtube_url> --lang en-IN --source tedtalk
python pipeline.py --url <youtube_url> --lang hi-IN --source podcast --start 00:01:10 --end 00:20:00
```

| Flag | Required | Description |
|------|----------|-------------|
| `--url` | Yes | YouTube URL |
| `--lang` | No | BCP-47 language code (default: `en-IN`) |
| `--source` | Yes | Source type label (e.g. `nptel`, `podcast`, `tedtalk`) |
| `--start` | No | Trim start timestamp (`HH:MM:SS`) |
| `--end` | No | Trim end timestamp (`HH:MM:SS`) |

### Individual modules

```bash
# Transcribe a single WAV
python transcribe.py audio.wav hi-IN

# Segment a WAV into clips
python segment.py input.wav output_dir/ prefix

# Tag emotion for a transcript
python tag_emotion.py "Your transcript text here"
```

## Dataset Output

```
dataset/
├── audio/                    # Accepted .wav segments (24kHz mono PCM)
│   └── en-IN_tedtalk_<id>_001.wav
├── rejected/                 # Segments that failed quality checks
├── metadata.jsonl            # Accepted segments
└── rejected_metadata.jsonl   # Rejected segments with rejection reason
```

### `metadata.jsonl` schema

```json
{
  "file": "en-IN_tedtalk_sNbGU_I9HWw_001.wav",
  "transcript": "...",
  "language": "en-IN",
  "source_type": "tedtalk",
  "emotion": "conversational",
  "duration_seconds": 23.381,
  "source_video": "sNbGU_I9HWw",
  "sample_rate": 24000
}
```

### Emotion/style tags

`neutral` · `formal` · `conversational` · `explanatory` · `narrative` · `excited` · `inspirational` · `sad` · `humorous` · `emotional`

### Quality filters

Segments are rejected if:
- Duration is outside **10–28 seconds**
- Transcript is fewer than **20 characters** or suspiciously long (>600 chars)
- Word rate exceeds **0.8 s/word** (likely ASR mismatch)
- Mean volume is below **−35 dB** (likely noise or silence)

## Upload to HuggingFace

```bash
huggingface-cli login
python upload_hf.py --repo your-username/tts-indian-en-hi

# Print stats without uploading
python upload_hf.py --repo your-username/tts-indian-en-hi --stats-only
```
