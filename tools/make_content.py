#!/usr/bin/env python3
"""Writes tomorrow's content.json with the Claude API (used by the daily GitHub workflow, so the nightly batch never depends on
anything else running). Needs ANTHROPIC_API_KEY. Skips if queue/<tomorrow>/ already has a plan.json or content.json.
    python3 tools/make_content.py            # tomorrow in South African time
    python3 tools/make_content.py 2026-11-21
Prints the day it made, or "exists" when there was nothing to do."""
import json, os, sys, re, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("POSTS_MODEL", "claude-sonnet-5-5")
SAST = timezone(timedelta(hours=2))
FLAVOUR = ["Monday: starting a business", "Tuesday: getting customers", "Wednesday: money",
           "Thursday: mindset or a myth", "Friday: getting found online", "Saturday: side hustles", "Sunday: community or a question"]
TOPICS = """getting your first customers; pricing your products and services; testing a business idea before spending money;
a one-page business plan; separating business and personal money; side hustle ideas for little money; building a simple brand;
time management for one-person businesses; handling difficult customers; when to go full time; setting up a Google Business Profile;
getting Google reviews; WhatsApp Business basics; writing a quote that wins the job; making a price list; following up politely on
unpaid invoices; repeat customers and referrals; taking better photos of your work; a simple social media routine; why a website helps"""

RULES = f"""You write tomorrow's three social posts for Lekker Hustle (lekkerhustle.co.za), a South African website builder for small
businesses and side hustlers. Audience: South African small business owners and side hustlers. Subject: HOW TO BUILD A BUSINESS and
entrepreneur tips. Topics you may draw on: {TOPICS}.

Mix: reel1 (06:30) one punchy entrepreneur tip; reel2 (12:30) a different angle (a myth, a mistake, a checklist); carousel (18:30) one
topic as 5 to 7 numbered steps. At most ONE of the three may mention the website builder; the others are pure advice.
Reels: 3 to 6 frames. FIRST frame a big, bold, curious or relatable hook (never a near-empty frame). Last frame: ONE call to action.
Frame keys: s (small line), b (big white words), h (gold highlight words), u (optional short line). Keep every line short.
If a hook promises "4 tips", there must be exactly 4 numbered frames. Carousel: a cover (kind "cover": small, big, hl, sub), numbered tip
slides (n, tag, title, head, body), and a last slide (kind "cta": small, big, hl, sub).
Captions: a hook on line 1, one or two short lines, ONE call to action (rotate: Save this / Send this to a friend who is starting out /
Free guides: link in bio / comment your question), then 3 to 5 hashtags from #smallbusinessSA #entrepreneurSA #sidehustleSA #startupSA
#moneytips #lekkerhustle (vary them).
PHOTO: reel1, reel2 and carousel each get "photo": 2 to 4 English search words for a stock photo that matches the post, specific and
visual (what is in the picture), e.g. "market stall owner", "notebook and calculator desk". Never anything that looks like a real brand,
business or famous person, no children.
HARD RULES: no emojis anywhere. Never invent statistics, quotes, clients, income figures or results. Do not claim Lekker Hustle features
that are not live (lead capture on published sites, remove-branding, blog writer, full online shop). If you mention pricing say exactly:
Free to build, R129 a month to publish. General advice only; no legal or tax specifics. Plain confident South African English, a little
humour, light slang is fine. Do not repeat any topic, hook or angle from the recent posts listed below.
Answer with ONLY the JSON object, no markdown, in this shape:
{{"reel1": {{"photo": "...", "frames": [{{"s": "", "b": "", "h": "", "u": ""}}], "caption": "..."}},
  "reel2": {{"photo": "...", "frames": [...], "caption": "..."}},
  "carousel": {{"photo": "...", "slides": [...], "caption": "..."}}}}"""


def recent_captions(today):
    out = []
    for d in sorted((ROOT / "queue").glob("20*"))[-21:]:
        for f in sorted(d.glob("post*.txt")):
            out.append(f"[{d.name} {f.stem}] " + f.read_text(encoding="utf-8").strip().split("\n")[0])
    return "\n".join(out) or "(none yet)"


def valid(c):
    try:
        for k in ("reel1", "reel2"):
            fr = c[k]["frames"]
            assert 3 <= len(fr) <= 6 and all(f.get("b") for f in fr) and c[k]["caption"].strip() and c[k].get("photo")
        sl = c["carousel"]["slides"]
        assert 6 <= len(sl) <= 9 and sl[0].get("kind") == "cover" and sl[-1].get("kind") == "cta"
        assert c["carousel"]["caption"].strip() and c["carousel"].get("photo")
        blob = json.dumps(c, ensure_ascii=False)
        assert not re.search(r"[\U0001F300-\U0001FAFF☀-➿]", blob)
        return True
    except Exception:
        return False


def ask(prompt):
    body = json.dumps({"model": MODEL, "max_tokens": 4000, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "content-type": "application/json", "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    txt = "".join(b.get("text", "") for b in data["content"])
    return json.loads(txt[txt.index("{"): txt.rindex("}") + 1])


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else (datetime.now(SAST) + timedelta(days=1)).strftime("%Y-%m-%d")
    folder = ROOT / "queue" / day
    if (folder / "plan.json").exists() or (folder / "content.json").exists():
        print("exists"); return
    wd = FLAVOUR[datetime.strptime(day, "%Y-%m-%d").weekday()]
    prompt = f"{RULES}\n\nThe posts are for {day} ({wd}). Weekly flavour: blend it in, do not force it.\n\nRecent posts (first lines of captions):\n{recent_captions(day)}"
    for attempt in range(4):
        try:
            c = ask(prompt)
            if valid(c):
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "content.json").write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                print(day); return
            print("attempt", attempt + 1, "invalid, retrying", file=sys.stderr)
        except Exception as e:
            print("attempt", attempt + 1, "failed:", repr(e)[:200], file=sys.stderr)
    sys.exit("could not make content")


main()
