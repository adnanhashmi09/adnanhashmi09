#!/usr/bin/env python3
"""Update Anton the Tamagotchi based on hours since Adnan's last commit anywhere."""
import os
import re
import sys
import json
import datetime as dt
from urllib.request import Request, urlopen
from urllib.error import HTTPError

USER = os.environ.get("GH_USER", "adnanhashmi09")
TOKEN = os.environ["GITHUB_TOKEN"]
REPO_ROOT = os.environ.get("GITHUB_WORKSPACE", ".")

API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "anton-tamagotchi",
}


def gh(path):
    req = Request(f"{API}{path}", headers=HEADERS)
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def latest_commit_iso():
    """Most recent commit by USER across any public repo, via search API."""
    try:
        data = gh(f"/search/commits?q=author:{USER}&sort=author-date&order=desc&per_page=1")
        items = data.get("items") or []
        if items:
            return items[0]["commit"]["author"]["date"]
    except HTTPError as e:
        print(f"search/commits failed: {e}", file=sys.stderr)
    try:
        events = gh(f"/users/{USER}/events?per_page=100")
        for ev in events:
            if ev.get("type") == "PushEvent":
                return ev["created_at"]
    except HTTPError as e:
        print(f"events failed: {e}", file=sys.stderr)
    return None


def fmt(hours):
    if hours < 1:
        return f"{int(hours*60)}m"
    if hours < 24:
        return f"{int(hours)}h"
    return f"{int(hours/24)}d"


def state_for(hours):
    if hours is None:
        return ("mystery", "Grandson of Anton is in a quantum state. Commit something to collapse the wavefunction.")
    if hours < 24:
        return ("happy", f"Grandson of Anton just ate. Last commit {fmt(hours)} ago. Glowing.")
    if hours < 48:
        return ("content", f"Grandson of Anton is content. Last fed {fmt(hours)} ago.")
    if hours < 72:
        return ("hungry", f"Grandson of Anton is getting hungry. {fmt(hours)} since last commit.")
    if hours < 120:
        return ("sad", f"Grandson of Anton is sad. It has been {fmt(hours)}. He keeps glancing at the door.")
    if hours < 168:
        return ("dying", f"Grandson of Anton is barely conscious. {fmt(hours)} without food. Push something. Anything.")
    return ("dead", f"Grandson of Anton has perished. {fmt(hours)} of neglect. He will revive on your next commit.")


# All faces and auras use BMP-only chars (no surrogate pairs needed).
SPRITES = {
    "happy":   {"face": "(\u25d5\u203f\u25d5)",                       "color": "#f4a261", "bg": "#fef3c7", "aura": "*"},
    "content": {"face": "(\u00b4\u30fb\u03c9\u30fb\uff40)",           "color": "#e9a86d", "bg": "#fef9e7", "aura": ""},
    "hungry":  {"face": "(\u00b4\u2022\u1d17\u2022\uff40)",           "color": "#d4956a", "bg": "#fff4e6", "aura": "?"},
    "sad":     {"face": "(\u3005_\u3005)",                            "color": "#a07a5a", "bg": "#e8e4dc", "aura": "..."},
    "dying":   {"face": "(\u2299\u3142\u2299)",                       "color": "#7a6450", "bg": "#d6d2cb", "aura": "\u2620"},
    "dead":    {"face": "(\u00d7_\u00d7)",                            "color": "#555555", "bg": "#cfcfcf", "aura": "RIP"},
    "mystery": {"face": "(\uff9f\u0414\uff9f)",                       "color": "#888888", "bg": "#eeeeee", "aura": "?"},
}


def make_svg(mood, status_text, hours):
    s = SPRITES[mood]
    age_label = fmt(hours) if hours is not None else "??"
    anim = ""
    if mood in ("happy", "content"):
        anim = '<animateTransform attributeName="transform" type="translate" values="0,0; 0,-6; 0,0" dur="1.4s" repeatCount="indefinite"/>'
    elif mood == "hungry":
        anim = '<animateTransform attributeName="transform" type="rotate" values="-3 200 110; 3 200 110; -3 200 110" dur="2.2s" repeatCount="indefinite"/>'
    elif mood in ("sad", "dying"):
        anim = '<animateTransform attributeName="transform" type="translate" values="0,0; 0,3; 0,0" dur="3s" repeatCount="indefinite"/>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 220" width="400" height="220" font-family="ui-monospace, SFMono-Regular, Menlo, monospace">
  <rect width="400" height="220" rx="14" fill="{s["bg"]}" stroke="#222" stroke-width="2"/>
  <text x="200" y="30" text-anchor="middle" font-size="14" fill="#333">ANTON \u2022 capybara \u2022 mood: {mood}</text>
  <g>{anim}
    <ellipse cx="200" cy="135" rx="78" ry="50" fill="{s["color"]}" stroke="#3a2a1c" stroke-width="2"/>
    <ellipse cx="200" cy="100" rx="50" ry="38" fill="{s["color"]}" stroke="#3a2a1c" stroke-width="2"/>
    <ellipse cx="170" cy="78" rx="9" ry="11" fill="{s["color"]}" stroke="#3a2a1c" stroke-width="2"/>
    <ellipse cx="230" cy="78" rx="9" ry="11" fill="{s["color"]}" stroke="#3a2a1c" stroke-width="2"/>
    <text x="200" y="108" text-anchor="middle" font-size="22" fill="#2a1a0a">{s["face"]}</text>
    <rect x="138" y="170" width="14" height="14" fill="{s["color"]}" stroke="#3a2a1c" stroke-width="2"/>
    <rect x="248" y="170" width="14" height="14" fill="{s["color"]}" stroke="#3a2a1c" stroke-width="2"/>
  </g>
  <text x="200" y="208" text-anchor="middle" font-size="13" fill="#444">last fed {age_label} ago {s["aura"]}</text>
</svg>'''


def update_readme(svg_path, status_text, mood):
    readme_path = os.path.join(REPO_ROOT, "README.md")
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    block = (
        "<!-- ANTON:START -->\n"
        "## Meet Grandson of Anton\n\n"
        f"<img src=\"./anton.svg\" alt=\"Anton the Tamagotchi - {mood}\" width=\"400\"/>\n\n"
        f"> {status_text}\n\n"
        "_Anton is a capybara who lives off Adnan's commits. Push code to feed him. "
        "Sad after 3 days, dying after 5, dead after 7. He revives on the next commit._\n"
        "<!-- ANTON:END -->"
    )

    if "<!-- ANTON:START -->" in content:
        content = re.sub(
            r"<!-- ANTON:START -->.*?<!-- ANTON:END -->",
            block,
            content,
            flags=re.DOTALL,
        )
    else:
        content = content.rstrip() + "\n\n" + block + "\n"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    last_iso = latest_commit_iso()
    if last_iso:
        last = dt.datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
        now = dt.datetime.now(dt.timezone.utc)
        hours = (now - last).total_seconds() / 3600.0
    else:
        hours = None

    mood, text = state_for(hours)
    svg = make_svg(mood, text, hours)

    svg_path = os.path.join(REPO_ROOT, "anton.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)

    update_readme(svg_path, text, mood)
    print(f"mood={mood} hours={hours} text={text}")


if __name__ == "__main__":
    main()
