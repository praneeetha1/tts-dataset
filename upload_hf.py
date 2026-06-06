"""
Upload the dataset to HuggingFace.
Usage:
    pip install datasets huggingface_hub
    huggingface-cli login
    python upload_hf.py --repo your-username/tts-indian-en-hi
"""
import argparse
import json
import os

DATASET_DIR = "dataset"
AUDIO_DIR = os.path.join(DATASET_DIR, "audio")
METADATA_FILE = os.path.join(DATASET_DIR, "metadata.jsonl")


def load_metadata():
    rows = []
    with open(METADATA_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def print_stats(rows):
    total_dur = sum(r["duration_seconds"] for r in rows)
    langs = {}
    emotions = {}
    for r in rows:
        langs[r["language"]] = langs.get(r["language"], 0) + r["duration_seconds"]
        emotions[r["emotion"]] = emotions.get(r["emotion"], 0) + 1

    print(f"\nDataset stats:")
    print(f"  Total segments : {len(rows)}")
    print(f"  Total duration : {total_dur/60:.1f} min ({total_dur:.0f}s)")
    print(f"\n  By language:")
    for lang, dur in sorted(langs.items()):
        print(f"    {lang}: {dur/60:.1f} min")
    print(f"\n  By emotion tag:")
    for tag, count in sorted(emotions.items(), key=lambda x: -x[1]):
        print(f"    {tag}: {count}")


def upload(repo_id):
    from datasets import Dataset, Audio
    from huggingface_hub import HfApi

    rows = load_metadata()
    print_stats(rows)

    # Add full audio paths
    for r in rows:
        r["audio"] = os.path.join(AUDIO_DIR, r["file"])

    missing = [r for r in rows if not os.path.exists(r["audio"])]
    if missing:
        print(f"\nWarning: {len(missing)} audio files missing — they will be skipped")
        rows = [r for r in rows if os.path.exists(r["audio"])]

    print(f"\nBuilding HuggingFace dataset ({len(rows)} rows)...")
    ds = Dataset.from_list(rows).cast_column("audio", Audio(sampling_rate=24000))

    print(f"Pushing to hub: {repo_id}")
    ds.push_to_hub(repo_id, private=False)
    print(f"\nDone! Dataset live at: https://huggingface.co/datasets/{repo_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="HuggingFace repo e.g. username/tts-indian-en-hi")
    parser.add_argument("--stats-only", action="store_true", help="Just print stats, don't upload")
    args = parser.parse_args()

    if args.stats_only:
        print_stats(load_metadata())
    else:
        upload(args.repo)
