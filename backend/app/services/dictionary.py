import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def fetch_word_profile(word: str) -> dict:
    normalized = (word or "").strip().lower()
    if not normalized:
        return {
            "phonetic": None,
            "part_of_speech": None,
            "meaning": None,
        }

    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{normalized}"

    try:
        with urlopen(url, timeout=8) as response:
            raw = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError):
        return {
            "phonetic": None,
            "part_of_speech": None,
            "meaning": None,
        }

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "phonetic": None,
            "part_of_speech": None,
            "meaning": None,
        }

    if not isinstance(payload, list) or not payload:
        return {
            "phonetic": None,
            "part_of_speech": None,
            "meaning": None,
        }

    first = payload[0]
    phonetic = first.get("phonetic")
    if not phonetic:
        phonetics = first.get("phonetics") or []
        for item in phonetics:
            text = item.get("text")
            if text:
                phonetic = text
                break

    part_of_speech = None
    meaning = None
    meanings = first.get("meanings") or []
    if meanings:
        part_of_speech = meanings[0].get("partOfSpeech")
        defs = meanings[0].get("definitions") or []
        if defs:
            meaning = defs[0].get("definition")

    return {
        "phonetic": phonetic,
        "part_of_speech": part_of_speech,
        "meaning": meaning,
    }
