#!/usr/bin/env python3
"""Smart Shelf Picks - social media pictures and videos, built with the website.

For every product in the sheet's "media" list it writes, under _site/m/<slug>/:
  post.jpg   1080x1350 clean photo + small brand bar  (Instagram + Facebook posts)
  pin1.jpg   1000x1500 photo + headline               (Pinterest)
  pin2.jpg   1000x1500 "why we love it" list          (Pinterest)
  pin3.jpg   1000x1500 gift-idea angle, closer crop   (Pinterest)
  reel.mp4   1080x1920, ~9 s slideshow                (Instagram/Facebook Reels, TikTok)
Run after build.py:  python3 media.py
"""
import glob, io, json, os, re, subprocess, sys, tempfile, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageOps

SCRIPT_URL = ("https://script.google.com/macros/s/"
              "AKfycbx6tZw0jPQTlla67Xbh-DZm9Gvogk9GMxrZORdfxJjfHSX2aEF4yNil7KdXalH6imhy/exec")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_site", "m")
SITE = "smartshelfpicks.github.io"
RUST, DARK, CREAM, ORANGE, WHITE = (160, 74, 18), (43, 33, 24), (255, 247, 238), (240, 163, 94), (255, 255, 255)
FONT_DIRS = ["/usr/share/fonts/truetype/dejavu/"]
MUSIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")
AUDIENCE = {
    "Kitchen Finds": "coffee & kitchen lovers", "Fitness & Recovery": "fitness fans", "Outdoor & Garden": "outdoor lovers",
    "Tech & Safety": "tech lovers", "Home & Decor": "cozy homebodies", "Gift Ideas": "everyone on your list",
    "Pet Picks": "pet parents", "Flowers & Treats": "anyone with a sweet tooth", "Kids & Family": "families",
    "Deals & Steals": "deal hunters", "Travel Essentials": "travelers", "Run & Ride": "runners & riders",
}


def font(size, bold=True):
    for d in FONT_DIRS:
        p = os.path.join(d, "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 smartshelfpicks-media"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def load_photo(url):
    im = Image.open(io.BytesIO(fetch(url)))
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, WHITE)
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert("RGB")


def fit(im, w, h, bg=WHITE):
    """Whole photo inside w x h, centred on bg (no cropping)."""
    c = ImageOps.contain(im, (w, h), Image.LANCZOS)
    out = Image.new("RGB", (w, h), bg)
    out.paste(c, ((w - c.width) // 2, (h - c.height) // 2))
    return out


def wrap(draw, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if draw.textlength(t, font=fnt) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def text_block(draw, xy, text, size, color, width, max_lines, bold=True, gap=1.22):
    x, y = xy
    while size > 18:
        fnt = font(size, bold)
        lines = wrap(draw, text, fnt, width)
        if len(lines) <= max_lines:
            break
        size -= 3
    lines = lines[:max_lines]
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=color)
        y += int(size * gap)
    return y


def split_name(name):
    m = re.match(r"^(black friday|cyber monday)\s*:\s*(.+)$", name, re.I)
    return (m.group(1).upper() + " DEAL", m.group(2)) if m else ("", name)


def reasons(caption):
    parts = [p.strip(" .!") for p in re.split(r"(?<=[.!?])\s+|,\s+(?:and\s+)?|\s+-\s+", caption or "") if len(p.strip()) > 8]
    return [p[0].upper() + p[1:] for p in parts][:3] or ["Hand-picked by Smart Shelf Picks"]


def brand_bar(img, h=86):
    d = ImageDraw.Draw(img)
    W, H = img.size
    d.rectangle([0, H - h, W, H], fill=DARK)
    d.text((36, H - h + (h - 34) // 2), "SMART SHELF PICKS", font=font(30), fill=ORANGE)
    f = font(24, False)
    d.text((W - 36 - d.textlength(SITE, font=f), H - h + (h - 26) // 2), SITE, font=f, fill=(232, 217, 204))


def make_post(photo):
    img = fit(photo, 1080, 1350 - 86)
    canvas = Image.new("RGB", (1080, 1350), WHITE)
    canvas.paste(img, (0, 0))
    brand_bar(canvas)
    return canvas


def make_pin1(photo, p):
    badge, name = split_name(p["name"])
    c = Image.new("RGB", (1000, 1500), WHITE)
    c.paste(fit(photo, 1000, 1000), (0, 0))
    d = ImageDraw.Draw(c)
    d.rectangle([0, 1000, 1000, 1500], fill=RUST)
    y = 1040
    if badge:
        d.text((60, y), badge, font=font(30), fill=(247, 210, 176)); y += 50
    else:
        d.text((60, y), p.get("category", "").upper(), font=font(28), fill=(247, 210, 176)); y += 48
    text_block(d, (60, y), name, 58, WHITE, 880, 4)
    d.text((60, 1430), SITE, font=font(30), fill=ORANGE)
    return c


def make_pin2(photo, p):
    badge, name = split_name(p["name"])
    c = Image.new("RGB", (1000, 1500), CREAM)
    d = ImageDraw.Draw(c)
    d.text((60, 56), "WHY WE LOVE IT", font=font(30), fill=RUST)
    y = text_block(d, (60, 104), name, 50, DARK, 880, 3)
    box = fit(photo, 880, 700)
    c.paste(box, (60, max(y + 24, 300)))
    y = max(y + 24, 300) + 700 + 36
    for r in reasons(p.get("caption")):
        d.ellipse([62, y + 12, 80, y + 30], fill=ORANGE)
        y = text_block(d, (100, y), r, 34, DARK, 840, 2, bold=False) + 14
        if y > 1380:
            break
    d.text((60, 1430), "Shop it at " + SITE, font=font(28), fill=RUST)
    return c


def make_pin3(photo, p):
    badge, name = split_name(p["name"])
    w, h = photo.size
    zoom = photo.crop((int(w * .1), int(h * .1), int(w * .9), int(h * .9)))  # closer view = a different-looking pin
    c = Image.new("RGB", (1000, 1500), (250, 236, 222))
    d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 1000, 300], fill=DARK)
    d.text((60, 60), "GIFT IDEA", font=font(64), fill=ORANGE)
    text_block(d, (60, 150), "for " + AUDIENCE.get(p.get("category", ""), "everyone on your list"), 46, WHITE, 880, 2)
    c.paste(fit(zoom, 900, 900, (250, 236, 222)), (50, 330))
    text_block(d, (60, 1260), name, 40, DARK, 880, 3)
    d.text((60, 1430), SITE, font=font(28), fill=RUST)
    return c


def reel_slides(photo, p):
    badge, name = split_name(p["name"])
    s1 = Image.new("RGB", (1080, 1920), WHITE)
    s1.paste(fit(photo, 1000, 1100), (40, 520))
    d = ImageDraw.Draw(s1)
    d.rectangle([0, 0, 1080, 480], fill=RUST)
    d.text((60, 70), (badge or p.get("category", "").upper()), font=font(34), fill=(247, 210, 176))
    text_block(d, (60, 130), name, 66, WHITE, 960, 4)
    s2 = Image.new("RGB", (1080, 1920), CREAM)
    d = ImageDraw.Draw(s2)
    d.text((60, 200), "WHY WE LOVE IT", font=font(44), fill=RUST)
    y = 300
    for r in reasons(p.get("caption")):
        d.ellipse([62, y + 18, 88, y + 44], fill=ORANGE)
        y = text_block(d, (110, y), r, 50, DARK, 900, 3) + 40
    s2.paste(fit(photo, 760, 760, CREAM), (160, max(y + 40, 1000)))
    s3 = Image.new("RGB", (1080, 1920), DARK)
    d = ImageDraw.Draw(s3)
    s3.paste(fit(photo, 700, 700, DARK), (190, 300))
    d.text((60, 1100), "Shop it:", font=font(70), fill=WHITE)
    d.text((60, 1200), "link in bio", font=font(70), fill=ORANGE)
    d.text((60, 1350), SITE, font=font(40, False), fill=(232, 217, 204))
    d.text((60, 1420), "→ " + p.get("category", "") + " section", font=font(36, False), fill=(232, 217, 204))
    return [s1, s2, s3]


def make_reel(photo, p, path):
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for i, s in enumerate(reel_slides(photo, p)):
            f = os.path.join(tmp, f"s{i}.jpg")
            s.save(f, quality=92)
            files.append(f)
        args = ["ffmpeg", "-y", "-loglevel", "error"]
        for f in files:
            args += ["-i", f]
        tracks = sorted(glob.glob(os.path.join(MUSIC, "*.m4a")) + glob.glob(os.path.join(MUSIC, "*.mp3")))
        if tracks:  # royalty-free background music, picked per product
            args += ["-i", tracks[sum(map(ord, p.get("slug", ""))) % len(tracks)]]
        else:
            args += ["-f", "lavfi", "-t", "9", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
        zoom = ";".join(f"[{i}:v]scale=1188:2112,zoompan=z='min(zoom+0.0007,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                        f":d=90:s=1080x1920:fps=30,setsar=1[v{i}]" for i in range(len(files)))
        args += ["-filter_complex", zoom + ";" + "".join(f"[v{i}]" for i in range(len(files))) + f"concat=n={len(files)}:v=1:a=0[v]",
                 "-map", "[v]", "-map", f"{len(files)}:a", "-af", "afade=t=out:st=8.3:d=0.7", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                 "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", path]
        subprocess.run(args, check=True, timeout=180)


def main():
    if len(sys.argv) > 1:
        feed = json.load(open(sys.argv[1], encoding="utf-8"))
    else:
        feed = json.loads(fetch(SCRIPT_URL + "?format=json").decode("utf-8"))
    items = feed.get("media") or []
    ok = bad = 0
    for p in items:
        slug = p.get("slug")
        if not slug or not p.get("image"):
            continue
        d = os.path.join(OUT, slug)
        os.makedirs(d, exist_ok=True)
        try:
            photo = load_photo(p["image"])
            make_post(photo).save(os.path.join(d, "post.jpg"), quality=90)
            make_pin1(photo, p).save(os.path.join(d, "pin1.jpg"), quality=90)
            make_pin2(photo, p).save(os.path.join(d, "pin2.jpg"), quality=90)
            make_pin3(photo, p).save(os.path.join(d, "pin3.jpg"), quality=90)
            make_reel(photo, p, os.path.join(d, "reel.mp4"))
            ok += 1
        except Exception as e:  # one bad image never stops the build
            bad += 1
            print("media skipped:", slug, "-", e)
    print(f"media: {ok} products done, {bad} skipped")


if __name__ == "__main__":
    main()
