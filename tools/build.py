#!/usr/bin/env python3
"""Builds one day's batch from a content file, in the Lekker Hustle post look
(black, flag-colour stripes, Bebas Neue headings, DM Sans text, gold highlight block).

    python3 tools/build.py queue/2026-11-19/content.json

Writes next to the content file: post1.mp4 + post1.txt (reel, 06:30), post2.mp4 + post2.txt (reel, 12:30),
post3-01.png ... + post3.txt (carousel, 18:30) and plan.json (all three "manual").
Needs Playwright (chromium) and ffmpeg. Reels are silent on purpose: add a trending sound in the app.
The same mp4 files can be uploaded to YouTube Shorts.

content.json:
{
 "reel1":    {"frames": [{"s": "SMALL LINE", "b": "BIG WHITE WORDS", "h": "GOLD HIGHLIGHT", "u": "optional line under"}], "caption": "...", "photo": "optional"},
 "reel2":    {"frames": [...], "caption": "..."},
 "carousel": {"slides": [
     {"kind": "cover", "small": "...", "big": "...", "hl": "...", "sub": "..."},
     {"n": 1, "tag": "Topic", "title": "SHORT TITLE", "head": "One bold line", "body": "One or two sentences."},
     {"kind": "cta", "small": "...", "big": "...", "hl": "...", "sub": "..."}], "caption": "..."}
}
4-6 frames per reel (about 3 s each), 5-8 carousel slides. One idea per frame or slide.
"photo" (optional, on a post or a single frame/slide): a file in tools/photos/, or "pexels:search words"
(fetched through our backend, which holds the Pexels key; cached in tools/photos/). It is shown faded behind the words.
"""
import json, sys, re, subprocess, shutil, base64
from pathlib import Path
from html import escape
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
G, GOLD, RED, BLUE, BLACK = "#007A4D", "#FFB612", "#DE3831", "#002395", "#0A0A0A"
FONTS = {n: base64.b64encode((HERE / "fonts" / f).read_bytes()).decode() for n, f in
         [("bebas", "bebas-neue-latin-400-normal.woff2"), ("dm4", "dm-sans-latin-400-normal.woff2"), ("dm7", "dm-sans-latin-700-normal.woff2")]}
LOGO = base64.b64encode((HERE / "logo.png").read_bytes()).decode()
PEXELS_API = "https://lekker-hustle-production.up.railway.app/api/pexels/search"

CSS = f"""
@font-face{{font-family:Bebas;src:url(data:font/woff2;base64,{FONTS['bebas']})}}
@font-face{{font-family:DM;font-weight:400;src:url(data:font/woff2;base64,{FONTS['dm4']})}}
@font-face{{font-family:DM;font-weight:700;src:url(data:font/woff2;base64,{FONTS['dm7']})}}
*{{box-sizing:border-box;margin:0}}
body{{font-family:DM,sans-serif;color:#fff;background:{BLACK}}}
.slide{{position:relative;overflow:hidden;background:{BLACK}}}
.stripe{{position:absolute;left:0;right:0;height:14px;display:flex}}.stripe i{{flex:1}}
.logo{{position:absolute;left:70px;top:62px;height:64px}}
.url{{position:absolute;left:70px;bottom:52px;font-weight:700;font-size:28px;opacity:.85}}
.hint{{position:absolute;right:70px;bottom:52px;font-size:26px;opacity:.55}}
.cover{{position:absolute;left:70px;right:70px;text-align:center}}
.cover .s{{font-weight:700;font-size:34px;letter-spacing:4px;color:{GOLD};text-transform:uppercase}}
.cover .b{{font-family:Bebas;letter-spacing:2px;line-height:1.0;text-transform:uppercase;margin-top:22px}}
.cover .h{{display:inline-block;background:{GOLD};color:{BLACK};padding:0 26px;margin-top:10px}}
.cover .u{{font-size:40px;color:#d8d8d8;margin-top:46px;line-height:1.4}}
.tip{{position:absolute;left:90px;right:90px}}
.tip .tag{{font-size:28px;color:#9a9a9a;letter-spacing:3px;text-transform:uppercase}}
.tip .num{{font-family:Bebas;color:{GOLD};font-size:170px;line-height:1}}
.tip h1{{font-family:Bebas;font-weight:400;font-size:104px;line-height:1.0;letter-spacing:2px;text-transform:uppercase;color:{GOLD};margin-top:6px}}
.tip h2{{font-size:46px;line-height:1.25;font-weight:700;margin-top:40px}}
.tip p{{font-size:38px;line-height:1.5;color:#cfcfcf;margin-top:26px}}
.dots{{position:absolute;left:0;right:0;display:flex;justify-content:center;gap:14px}}
.dots i{{width:14px;height:14px;border-radius:7px;background:#3a3a3a}}.dots i.on{{background:{GOLD};width:44px}}
"""
STRIPES = "".join(f'<i style="background:{c}"></i>' for c in (G, GOLD, RED, BLUE))


def get_photo(photo):
    """photo = a file in tools/photos/, or 'pexels:search words'. Returns bytes or None."""
    if not photo:
        return None
    cache = HERE / "photos"; cache.mkdir(exist_ok=True)
    if not photo.startswith("pexels:"):
        f = cache / photo
        return f.read_bytes() if f.exists() else None
    q = photo[7:].strip()
    f = cache / (re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-") + ".jpg")
    if f.exists():
        return f.read_bytes()
    try:
        import urllib.request, urllib.parse
        data = json.loads(urllib.request.urlopen(f"{PEXELS_API}?q={urllib.parse.quote(q)}&per_page=5", timeout=20).read())
        src = (data.get("photos") or [{}])[0].get("src") or {}
        img = urllib.request.urlopen(src.get("large") or src.get("landscape") or src.get("medium"), timeout=30).read()
        f.write_bytes(img)
        return img
    except Exception as e:
        print("no photo for", q, "-", e)
        return None


def photo_layer(photo, strong):
    img = get_photo(photo)
    if not img:
        return ""
    return (f'<div style="position:absolute;inset:0;background:url(data:image/jpeg;base64,{base64.b64encode(img).decode()}) center/cover;'
            f'opacity:{.30 if strong else .20}"></div><div style="position:absolute;inset:0;background:linear-gradient(rgba(10,10,10,.35),rgba(10,10,10,.55))"></div>')


def big_size(txt, tall):
    n = len(txt)
    base = 200 if tall else 150
    return base if n <= 18 else int(base * .82) if n <= 32 else int(base * .68) if n <= 52 else int(base * .56)


def wrap(w, h, inner, photo=None, strong=False, extra=""):
    return f"""<html><head><style>{CSS}</style></head><body><div class="slide" style="width:{w}px;height:{h}px">
{photo_layer(photo, strong)}<div class="stripe" style="top:0">{STRIPES}</div><div class="stripe" style="bottom:0">{STRIPES}</div>
<img class="logo" src="data:image/png;base64,{LOGO}">{inner}<div class="url">lekkerhustle.co.za</div>{extra}</div></body></html>"""


def cover_html(w, h, small, big, hl, sub, photo=None):
    tall = h > 1500
    sz = big_size((big or "") + " " + (hl or ""), tall)
    top = 560 if tall else 300
    inner = (f'<div class="cover" style="top:{top}px"><div class="s">{escape(small or "")}</div>'
             f'<div class="b" style="font-size:{sz}px">{escape(big or "")}'
             + (f'<br><span class="h">{escape(hl)}</span>' if hl else "") + '</div>'
             + (f'<div class="u">{escape(sub)}</div>' if sub else "") + '</div>')
    return wrap(w, h, inner, photo, strong=True)


def tip_html(w, h, s, idx, total, photo=None):
    inner = (f'<div class="tip" style="top:210px">'
             + (f'<div class="num">{escape(str(s["n"]))}</div>' if s.get("n") else "")
             + (f'<div class="tag">{escape(s.get("tag", ""))}</div>' if s.get("tag") else "")
             + (f'<h1>{escape(s["title"])}</h1>' if s.get("title") else "")
             + (f'<h2>{escape(s["head"])}</h2>' if s.get("head") else "")
             + (f'<p>{escape(s["body"])}</p>' if s.get("body") else "") + '</div>')
    dots = f'<div class="dots" style="bottom:70px">{"".join(f"<i class=on></i>" if k == idx else "<i></i>" for k in range(total))}</div>'
    return wrap(w, h, inner, photo, extra=dots + (f'<div class="hint" style="bottom:110px">{idx + 1}/{total}</div>' if False else ""))


def shot(page, html, out, w, h):
    page.set_viewport_size({"width": w, "height": h})
    page.set_content(html)
    page.wait_for_timeout(250)
    page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": w, "height": h})


def frame_html(f, photo, idx, total):
    """A reel frame: s = small line, b = big words, h = highlight, u = line under. Last frame is the call to action."""
    return cover_html(1080, 1920, f.get("s", ""), f.get("b", ""), f.get("h", ""), f.get("u", ""), f.get("photo") or photo)


def slide_html(s, photo, idx, total):
    if s.get("kind") in ("cover", "cta"):
        return cover_html(1080, 1350, s.get("small", ""), s.get("big", ""), s.get("hl", ""), s.get("sub", ""), s.get("photo") or photo)
    return tip_html(1080, 1350, s, idx, total, s.get("photo") or photo)


def main(cfile: Path):
    day = cfile.parent
    c = json.loads(cfile.read_text())
    for k in ("reel1", "reel2", "carousel"):
        if k not in c:
            sys.exit(f'content.json needs "{k}"')
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_page()
        for n, key in ((1, "reel1"), (2, "reel2")):
            reel = c[key]; tmp = day / f"_frames{n}"; tmp.mkdir(exist_ok=True)
            fs = reel["frames"]
            for i, f in enumerate(fs, 1):
                shot(page, frame_html(f, reel.get("photo"), i, len(fs)), tmp / f"f{i}.png", 1080, 1920)
            sec = reel.get("seconds", 3)
            (tmp / "list.txt").write_text("".join(f"file 'f{i}.png'\nduration {sec}\n" for i in range(1, len(fs) + 1)) + f"file 'f{len(fs)}.png'\n")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                            "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-an", str(day / f"post{n}.mp4")], check=True)
            shutil.rmtree(tmp)
            (day / f"post{n}.txt").write_text(reel["caption"].strip() + "\n")
        sl = c["carousel"]["slides"]
        for i, s in enumerate(sl):
            shot(page, slide_html(s, c["carousel"].get("photo"), i, len(sl)), day / f"post3-{i + 1:02d}.png", 1080, 1350)
        (day / "post3.txt").write_text(c["carousel"]["caption"].strip() + "\n")
        b.close()
    plan = {"posts": [
        {"slot": 1, "time": "06:30", "type": "reel", "mode": "manual", "files": ["post1.mp4"], "caption": "post1.txt"},
        {"slot": 2, "time": "12:30", "type": "reel", "mode": "manual", "files": ["post2.mp4"], "caption": "post2.txt"},
        {"slot": 3, "time": "18:30", "type": "carousel", "mode": "manual", "files": [f"post3-{i + 1:02d}.png" for i in range(len(sl))], "caption": "post3.txt"}]}
    (day / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print("built", day)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
