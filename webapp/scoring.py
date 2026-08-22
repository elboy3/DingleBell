"""AI taste-match scoring: given a listing's photo and a written taste
profile, ask Claude how well the photo matches, as a 0-100 score plus a
one-sentence reasoning. Called synchronously from browser_import.py right
after a new listing is saved - see that module's docstring for why that's
safe here (this pivot explicitly de-prioritizes speed).

Every failure mode (no photo, fetch failure, API error, unparseable
response) returns (None, None) and never raises - ingestion must never
block on scoring. Matches filters.py's existing "unknown field, don't
block on it" pattern."""

import base64
import json
import re

import anthropic
import requests

MODEL = "claude-opus-5"

_PROMPT_TEMPLATE = """You are helping evaluate an apartment listing photo against a \
couple's stated taste profile.

Taste profile:
{taste_profile}

Judge ONLY the space shown in the photo - its style, finishes, layout, light. Ignore \
photography/staging quality: a great apartment shot badly should not score low, and a \
mediocre apartment staged well should not score high.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{{"score": <integer 0-100, how well this matches the taste profile>, \
"reasoning": "<one short sentence citing the specific visual cue that drove the score>"}}"""


def _extract_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except (ValueError, TypeError):
        return None


def score_listing(listing: dict, taste_profile: str, api_key: str) -> tuple[int | None, str | None]:
    photo_url = listing.get("photo_url")
    if not photo_url:
        return None, None

    try:
        photo_resp = requests.get(photo_url, timeout=8)
        if photo_resp.status_code != 200:
            return None, None
        media_type = photo_resp.headers.get("content-type", "image/jpeg").split(";")[0]
        if not media_type.startswith("image/"):
            return None, None
        image_data = base64.standard_b64encode(photo_resp.content).decode("utf-8")
    except requests.RequestException:
        return None, None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            output_config={"effort": "low"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": _PROMPT_TEMPLATE.format(taste_profile=taste_profile),
                        },
                    ],
                }
            ],
        )
    except (anthropic.APIError, anthropic.APIConnectionError):
        return None, None

    if response.stop_reason == "refusal":
        return None, None

    text = next((b.text for b in response.content if b.type == "text"), "")
    parsed = _extract_json(text)
    if not parsed:
        return None, None

    score = parsed.get("score")
    reasoning = parsed.get("reasoning")
    if not isinstance(score, int) or not (0 <= score <= 100) or not isinstance(reasoning, str):
        return None, None

    return score, reasoning
