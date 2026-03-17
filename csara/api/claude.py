import os
import sys
import json
import urllib.request
import urllib.error

CSARA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_api_key() -> str:
    env_path = os.path.join(CSARA_DIR, ".env")
    if not os.path.exists(env_path):
        return ""
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


# Global debug flag — set by CLI entry points
_debug = False


def set_debug(enabled: bool) -> None:
    global _debug
    _debug = enabled


def _dbg(label: str, msg: str) -> None:
    if _debug:
        print(f"  [DEBUG claude] {label}: {msg}", file=sys.stderr)


def call_claude(system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
    api_key = _load_api_key()
    if not api_key or api_key == "your_key_here":
        print("Error: ANTHROPIC_API_KEY not set in csara/.env", file=sys.stderr)
        return ""

    _dbg("system_prompt", system_prompt[:200] + ("..." if len(system_prompt) > 200 else ""))
    _dbg("user_message", user_message[:300] + ("..." if len(user_message) > 300 else ""))
    _dbg("max_tokens", str(max_tokens))

    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}]
    }

    data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            result = json.loads(raw)
            text = result["content"][0]["text"]
            _dbg("response", text[:300] + ("..." if len(text) > 300 else ""))
            return text
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, json.JSONDecodeError) as e:
        _dbg("error", str(e))
        print(f"Claude API error: {e}", file=sys.stderr)
        return ""
