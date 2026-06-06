"""
Run the full pipeline for a single video.
Edit the variables below and run: python test_pipeline.py
"""
from pipeline import run

# ── Edit these for each video ──────────────────────────────────────────
URL    = None
LANG   = "hi-IN"              # e.g. en-IN, hi-IN, te-IN, ta-IN, ml-IN
SOURCE = "motivational_hindi" # e.g. nptel, tedtalk, podcast, news
START  = None                 # trim start (set to None to use full video)
END    = "00:05:00"           # trim end   (set to None to use full video)
# ───────────────────────────────────────────────────────────────────────

LOCAL_FILE = "/Users/praneetha.rao/Downloads/rough/motivational_hindi.mp3"  # set to None to download instead

if __name__ == "__main__":
    written = run(URL or LOCAL_FILE, LANG, SOURCE, start=START, end=END, local_file=LOCAL_FILE)
    print(f"\nDone. {written} segments written to dataset/")
