# Lekker Hustle daily social posts

The website (backend, social_posts.py) reads this repo and, at 18:00 SA time every evening, emails Ruan tomorrow's three
posts with a "Save post N" button for each. Everything here goes public on Instagram and YouTube Shorts anyway, so the
repo is public. Never put keys or private files here. Nothing is posted automatically.

## One folder per day

```
queue/2026-11-19/
  content.json     (the words; input for tools/build.py)
  plan.json
  post1.mp4        post1.txt      (reel, 06:30)
  post2.mp4        post2.txt      (reel, 12:30)
  post3-01.png ... post3-07.png   post3.txt   (carousel, 18:30)
```

`plan.json`:

```json
{ "posts": [
  { "slot": 1, "time": "06:30", "type": "reel",     "mode": "manual", "files": ["post1.mp4"], "caption": "post1.txt" },
  { "slot": 2, "time": "12:30", "type": "reel",     "mode": "manual", "files": ["post2.mp4"], "caption": "post2.txt" },
  { "slot": 3, "time": "18:30", "type": "carousel", "mode": "manual", "files": ["post3-01.png", "post3-02.png"], "caption": "post3.txt" } ] }
```

- Times are Cape Town time. `type`: `reel` (one mp4), `carousel` (2-10 png/jpg, in order) or `image` (one png/jpg).
- File names: letters, numbers, `.`, `_`, `-` only. Reels: mp4 (H.264) 1080x1920 under 90 s. Carousel slides: 1080x1350.
- Captions: plain UTF-8 text exactly as it should appear, hook on line 1, ONE call to action, 3-5 hashtags at the end.
- The same reels are uploaded to YouTube Shorts; the save page shows a title and description to copy.

## Build a day

```
python3 tools/build.py queue/YYYY-MM-DD/content.json
```

Needs Playwright (chromium) and ffmpeg. See the header of `tools/build.py` for the content.json format.
Push the batch before 17:30 SA time so the 18:00 email can include it. `sample/` is a trial day, never emailed.

## Content rules

Audience: South African small business owners and side hustlers. Topics: how to build a business, entrepreneur tips,
getting customers, pricing, money habits, side hustles, using a website to be found. Only real, checkable facts; never invent
clients, quotes, results or statistics; no emojis on slides; do not advertise features Lekker Hustle has not built.
