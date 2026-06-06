"""
Re-run emotion tagging on tedtalk entries in dataset/metadata.jsonl.
Overwrites the emotion field in-place using the current tag_emotion logic.

Usage: python retag_emotions.py
"""
import json
import os
from sarvamai import SarvamAI
from tag_emotion import tag_emotion

METADATA_FILE = os.path.join("dataset", "metadata.jsonl")
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
if not SARVAM_API_KEY:
    raise EnvironmentError("SARVAM_API_KEY env var not set")


def retag():
    with open(METADATA_FILE, "r") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    to_tag = [r for r in rows if r.get("source_type") == "tedtalk"]
    print(f"{len(to_tag)} tedtalk entries to retag, {len(rows) - len(to_tag)} others untouched\n")

    client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

    for row in to_tag:
        old = row.get("emotion", "?")
        new = tag_emotion(row["transcript"], client=client)
        row["emotion"] = new
        changed = " (changed)" if old != new else ""
        print(f"  {row['file']} | {old} → {new}{changed}")

    with open(METADATA_FILE, "w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nDone. {METADATA_FILE} updated.")


if __name__ == "__main__":
    retag()
