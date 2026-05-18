import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings


ALLOWED_RISK_LEVELS = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "IGNORE"}
FALLBACK_AI_ANALYSIS = {
    "is_risky": True,
    "risk_level": "MEDIUM",
    "confidence_score": 0.5,
    "reason": "AI analysis failed, using scanner result as fallback.",
    "recommendation": "Review this detection manually.",
}


def _build_safe_detection_context(detection: dict) -> dict:
    """Build AI context without sending the full raw secret value."""
    raw_value = detection.get("raw_value", "")
    masked_value = detection.get("masked_value", "")
    line_content = detection.get("line_content", "")

    # Gemini should not receive full secrets unnecessarily. Replace the raw
    # value in the code line with the masked value before building the prompt.
    if raw_value and masked_value:
        line_content = line_content.replace(raw_value, masked_value)

    return {
        "file_path": detection.get("file_path", "unknown"),
        "line_number": detection.get("line_number"),
        "line_content": line_content,
        "secret_type": detection.get("secret_type", "unknown"),
        "masked_value": masked_value,
        "confidence_hint": detection.get("confidence_hint", "unknown"),
        "detection_method": detection.get("detection_method", "unknown"),
        "entropy_score": detection.get("entropy_score"),
    }


def _build_prompt(safe_detection: dict) -> str:
    """Create a focused prompt that asks Gemini for JSON only."""
    # Regex and entropy find suspicious values quickly. Gemini adds context so
    # obvious test, dummy, or example values can be treated as lower risk.
    # The returned JSON shape is ready for a later Supabase storage phase.
    return f"""
You are analyzing a possible leaked credential found in a GitHub commit.

Regex and entropy scanning find suspicious values, but they can produce false positives.
Your job is to reduce false positives by reviewing the masked value and surrounding context.
The full raw secret is intentionally not provided unless absolutely necessary.
This AI result will later be stored in Supabase with the scanner result.

Consider:
- whether the value looks like a real secret or fake/test/example content
- the file path
- the variable name or surrounding code
- the detection method
- whether this appears to be dummy, sample, placeholder, or low-risk content

Use only these risk levels:
CRITICAL, HIGH, MEDIUM, LOW, IGNORE

Return only valid JSON in this exact shape:
{{
  "is_risky": true,
  "risk_level": "HIGH",
  "confidence_score": 0.91,
  "reason": "Short explanation.",
  "recommendation": "Short recommendation."
}}

Detection context:
{json.dumps(safe_detection, indent=2)}
""".strip()


def _parse_ai_json(response_text: str) -> dict:
    """Parse Gemini JSON and normalize fields to the expected shape."""
    response_text = response_text.strip()
    if response_text.startswith("```"):
        response_text = response_text.strip("`")
        response_text = response_text.replace("json", "", 1).strip()

    parsed = json.loads(response_text)

    risk_level = str(parsed.get("risk_level", "MEDIUM")).upper()
    if risk_level not in ALLOWED_RISK_LEVELS:
        risk_level = "MEDIUM"

    confidence_score = float(parsed.get("confidence_score", 0.5))
    confidence_score = max(0.0, min(confidence_score, 1.0))

    return {
        "is_risky": bool(parsed.get("is_risky", risk_level != "IGNORE")),
        "risk_level": risk_level,
        "confidence_score": confidence_score,
        "reason": str(parsed.get("reason", "")),
        "recommendation": str(parsed.get("recommendation", "")),
    }


def _analyze_with_google_genai(prompt: str) -> dict:
    """Use the official Google Gen AI SDK when it is installed."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    return _parse_ai_json(response.text)


def _analyze_with_rest_api(prompt: str) -> dict:
    """Use Gemini REST API as a Windows ARM64-friendly fallback."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
        },
    }
    request_body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=30) as response:
        response_body = response.read().decode("utf-8")

    response_data = json.loads(response_body)
    response_text = response_data["candidates"][0]["content"]["parts"][0]["text"]

    return _parse_ai_json(response_text)


def analyze_secret_with_ai(detection: dict) -> dict:
    """Ask Gemini to classify a scanner detection without logging raw secrets."""
    if not settings.gemini_api_key:
        return FALLBACK_AI_ANALYSIS.copy()

    safe_detection = _build_safe_detection_context(detection)
    prompt = _build_prompt(safe_detection)

    try:
        return _analyze_with_google_genai(prompt)
    except ImportError:
        try:
            return _analyze_with_rest_api(prompt)
        except (HTTPError, URLError, KeyError, IndexError, json.JSONDecodeError):
            return FALLBACK_AI_ANALYSIS.copy()
    except Exception:
        return FALLBACK_AI_ANALYSIS.copy()
