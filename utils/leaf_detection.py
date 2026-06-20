from __future__ import annotations

import base64
import itertools
import os

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# ── Paid Gemini API key ───────────────────────────────────────────────────────
_RAW_KEYS: list[str] = [
    k for k in [
        os.getenv("GEMINI_PAID"),  # paid key
    ]
    if k and k.strip()
]

print(f"[leaf] Loaded {len(_RAW_KEYS)} Gemini API key(s)")

_KEY_CYCLE = itertools.cycle(_RAW_KEYS) if _RAW_KEYS else None

GEMINI_LEAF_MODEL = "gemini-2.5-flash-lite"

VALID_CLASSES = {
    "BlackPoint",
    "FusariumFootRot",
    "HealthyLeaf",
    "LeafBlight",
    "WheatBlast",
}


def _next_key() -> str | None:
    return next(_KEY_CYCLE) if _KEY_CYCLE else None


class LeafValidationError(ValueError):
    pass


def predict_leaf(image_bytes: bytes, threshold: float = 0.5) -> dict[str, object]:
    if not _RAW_KEYS:
        print("[leaf] ⚠️  No API key found — skipping validation")
        return {
            "is_leaf": True,
            "confidence": 1.0,
            "detected_class": None,
            "message": "Gemini API key not configured, skipping validation.",
        }

    image_data = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """You are a wheat disease detection assistant.

Look at this image carefully and classify it into EXACTLY one of these 5 categories:

1. BlackPoint       - Wheat grain with dark/black discoloration at tip
2. FusariumFootRot  - Wheat stem/root with brown rot at base
3. HealthyLeaf      - Normal green healthy wheat leaf or plant
4. LeafBlight       - Wheat leaf with yellow/brown blight spots or lesions
5. WheatBlast       - Wheat spike/head with bleached appearance

If the image does NOT show wheat at all (animal, human, car, other crop, random object, other plant disease not in this list) — reply: INVALID

Reply with ONLY one word from this list:
BlackPoint | FusariumFootRot | HealthyLeaf | LeafBlight | WheatBlast | INVALID

No explanation. One word only."""

    # Try the key (only one key now, so this loop runs once)
    for attempt in range(len(_RAW_KEYS)):
        api_key = _next_key()
        key_hint = f"...{api_key[-6:]}" if api_key else "None"
        print(f"[leaf] Attempt {attempt + 1}/{len(_RAW_KEYS)} using key {key_hint}")

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(GEMINI_LEAF_MODEL)

            response = model.generate_content([
                {"mime_type": "image/jpeg", "data": image_data},
                prompt,
            ])

            answer = response.text.strip()
            answer = answer.split()[0] if answer.split() else "INVALID"
            print(f"[leaf] ✅ Gemini response: {answer}")

            if answer in VALID_CLASSES:
                return {
                    "is_leaf": True,
                    "confidence": 1.0,
                    "detected_class": answer,
                    "message": f"Wheat image detected ✅ ({answer})",
                }
            else:
                return {
                    "is_leaf": False,
                    "confidence": 0.0,
                    "detected_class": None,
                    "message": "Invalid image! Please upload a wheat plant image only. (BlackPoint, FusariumFootRot, HealthyLeaf, LeafBlight, or WheatBlast)",
                }

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower():
                print(f"[leaf] ⚠️  Key {key_hint} quota exceeded.")
                continue
            else:
                print(f"[leaf] ❌ Gemini error: {e}")
                return {
                    "is_leaf": False,
                    "confidence": 0.0,
                    "detected_class": None,
                    "message": "Service temporarily unavailable. Please try again later.",
                }

    # Key quota khatam
    print("[leaf] ❌ API key quota exceeded!")
    return {
        "is_leaf": False,
        "confidence": 0.0,
        "detected_class": None,
        "message": "Validation service quota exceeded. Please try again later.",
    }


def assert_leaf(image_bytes: bytes, threshold: float = 0.5) -> dict[str, object]:
    result = predict_leaf(image_bytes=image_bytes, threshold=threshold)
    if not result["is_leaf"]:
        raise LeafValidationError(result["message"])
    return result