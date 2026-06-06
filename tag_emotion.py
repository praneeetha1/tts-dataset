import os
import time
from sarvamai import SarvamAI

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")

VALID_TAGS = {
    "neutral",        # flat, no strong emotion
    "formal",         # structured, professional
    "conversational", # casual, natural
    "explanatory",    # teaching, breaking down concepts
    "narrative",      # storytelling
    "excited",        # high energy
    "inspirational",  # motivational speeches
    "sad",            # emotional, sombre
    "humorous",       # light, funny
    "emotional",      # heartfelt, emotive
}

PROMPT_TEMPLATE = """Classify the speaking style and emotion of this speech transcript.
Choose the single most appropriate tag from this list:
neutral, formal, conversational, explanatory, narrative, excited, inspirational, sad, humorous, emotional

Rules:
- Return ONLY the single tag word, nothing else
- Only use "neutral" if no other tag fits — it is a last resort
- "neutral" = flat delivery, no strong emotion or style — last resort only if nothing else fits
- "formal" = structured, professional, academic — speaker maintains distance and authority, no casual asides
- "conversational" = casual, natural, feels like talking to someone — contractions, asides, direct address to audience
- "explanatory" = teaching mode — breaking down a concept step by step, defining terms, guiding the listener through logic
- "narrative" = storytelling — recounting events, describing a sequence of what happened, past tense journey
- "excited" = high energy, enthusiastic — speaker is visibly pumped, fast pace, lots of emphasis
- "inspirational" = motivational, uplifting — speaker wants the listener to believe something is possible or to take action
- "sad" = sombre, mournful — slow, heavy tone about loss, failure, or hardship without personal vulnerability
- "humorous" = light, playful, funny — jokes, wit, or self-deprecation that makes the listener laugh
- "emotional" = heartfelt, vulnerable, grief, loss, or deeply personal — use when the speaker expresses genuine feeling, not just facts

Transcript:
{transcript}"""


def tag_emotion(transcript, client=None):
    """
    Returns an emotion/style tag string for the given transcript.
    Falls back to 'neutral' if the LLM returns something unexpected.
    """
    if client is None:
        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

    if not transcript or len(transcript.strip()) < 10:
        return "neutral"

    prompt = PROMPT_TEMPLATE.format(transcript=transcript[:1000])

    for attempt in range(3):
        try:
            response = client.chat.completions(
                messages=[{"role": "user", "content": prompt}],
                model="sarvam-30b"
            )
            msg = response.choices[0].message
            raw = msg.content or msg.reasoning_content or ""
            tag = raw.strip().lower().split()[0].rstrip(".,;:") if raw.strip() else "neutral"
            return tag if tag in VALID_TAGS else "neutral"
        except Exception as e:
            if attempt < 2:
                print(f"  tag_emotion retry {attempt + 1}/3: {e}")
                time.sleep(2)
            else:
                return "neutral"


if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "The state of a quantum system is described by a vector in a linear vector space. "
        "This is the foundational concept we need to understand before moving forward."
    )
    print(f"Transcript: {text[:100]}...")
    tag = tag_emotion(text)
    print(f"Emotion tag: {tag}")
