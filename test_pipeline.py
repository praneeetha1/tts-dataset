"""
Run the full pipeline for a single video.
Edit the variables below and run: python test_pipeline.py
"""
from pipeline import run

# ── Edit these for each video ──────────────────────────────────────────
URL    = None
LANG   = "te-IN"              # e.g. en-IN, hi-IN, te-IN, ta-IN, ml-IN
SOURCE = "movie_recap"        # e.g. nptel, tedtalk, podcast, news
START  = "00:03:21"           # trim start (set to None to use full video)
END    = "00:08:21"           # trim end   (set to None to use full video)
# ───────────────────────────────────────────────────────────────────────

LOCAL_FILE = "/Users/praneetha.rao/Downloads/rough/movie_recap_tel.mp4"  # set to None to download instead

if __name__ == "__main__":
    written = run(URL or LOCAL_FILE, LANG, SOURCE, start=START, end=END, local_file=LOCAL_FILE)
    print(f"\nDone. {written} segments written to dataset/")
