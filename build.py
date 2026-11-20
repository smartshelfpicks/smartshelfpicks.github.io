#!/usr/bin/env python3
"""Builds the Smart Shelf Picks static site from the product Google Sheet.

The Sheet's Apps Script publishes a JSON feed (only rows with "Show on site" = Yes).
This script turns it into plain HTML pages in ./_site, ready for GitHub Pages.
Run locally:  python3 build.py            (fetches the live feed)
              python3 build.py feed.json  (uses a saved copy)
"""
import html, json, os, re, shutil, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

SITE_URL = "https://smartshelfpicks.github.io"
SCRIPT_URL = ("https://script.google.com/macros/s/"
              "AKfycbx6tZw0jPQTlla67Xbh-DZm9Gvogk9GMxrZORdfxJjfHSX2aEF4yNil7KdXalH6imhy/exec")
FEED_URL = SCRIPT_URL + "?format=json"
OUT = "_site"
ROOT = os.path.dirname(os.path.abspath(__file__))

CATEGORIES = [
    ("Deals & Steals", "deals-steals", "Big markdowns on products people actually keep using, including certified refurbished picks from the brands themselves."),
    ("Fitness & Recovery", "fitness-recovery", "Home gym gear, recovery tools and workout essentials we think are worth it."),
    ("Run & Ride", "run-ride", "Running shoes, cycling gear and trackers for your daily miles."),
    ("Home & Decor", "home-decor", "Cozy, useful upgrades for every room, from heaters to cleaning helpers."),
    ("Kitchen Finds", "kitchen-finds", "Appliances and small upgrades that make everyday cooking and coffee better."),
    ("Gift Ideas", "gift-ideas", "Thoughtful gifts for music lovers, readers, makers and everyone in between."),
    ("Tech & Safety", "tech-safety", "Gadgets, home security and online safety tools that just work."),
    ("Travel Essentials", "travel-essentials", "Trackers, chargers and gear that make trips smoother."),
    ("Flowers & Treats", "flowers-treats", "Sweet treats and lasting bouquets to send or keep."),
    ("Outdoor & Garden", "outdoor-garden", "Camping, backyard and garden gear for time outside."),
    ("Kids & Family", "kids-family", "Safe, practical and fun picks for kids and busy parents."),
    ("Pet Picks", "pet-picks", "Comfy beds, cleanup helpers and treats for dogs and cats."),
]
CAT_BY_NAME = {c[0]: c for c in CATEGORIES}

STORES = [  # (text found in the link or its destination, store name)
    ("ebay.", "eBay"), ("lasko", "Lasko"), ("ritfit", "RitFit"), ("bigagnes", "Big Agnes"),
    ("maestri", "Maestri House"), ("fender", "Fender"), ("arcctv", "ARCCTV"), ("sweetjoy", "Sweet Joy Bites"),
    ("axkid", "Axkid"), ("noahpaw", "NOAH & PAW"), ("noahandpaw", "NOAH & PAW"), ("hollypine", "Holly & Pine"),
    ("hollyandpine", "Holly & Pine"), ("simzy", "Simzy"), ("nordvpn", "NordVPN"), ("etsy", "Etsy"),
    ("walmart", "Walmart"), ("target.com", "Target"), ("amazon.", "Amazon"),
]

e = html.escape


def slugify(s):
    s = re.sub(r"^(black friday|cyber monday)\s*:\s*", "", s, flags=re.I)
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:70].rstrip("-") or "item"


def store_of(link):
    low = link.lower()
    try:
        dest = urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("u", [""])[0].lower()
    except Exception:
        dest = ""
    for key, name in STORES:
        if key in low or key in dest:
            return name
    return "the retailer"


def load_feed():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            return json.load(f)
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "smartshelfpicks-site-builder"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def prepare(products):
    seen, out = set(), []
    for i, p in enumerate(products):
        name = (p.get("name") or "").strip()
        if not name or not p.get("link") or not p.get("image"):
            continue
        badge = ""
        m = re.match(r"^(black friday|cyber monday)\s*:\s*(.+)$", name, flags=re.I)
        if m:
            badge, name = m.group(1).title(), m.group(2).strip()
        slug = slugify(name)
        base, n = slug, 2
        while slug in seen:
            slug, n = f"{base}-{n}", n + 1
        seen.add(slug)
        cat = p.get("category") or "Deals & Steals"
        if cat not in CAT_BY_NAME:
            cat = "Deals & Steals"
        out.append({
            "name": name, "badge": badge, "slug": slug, "cat": cat, "cat_slug": CAT_BY_NAME[cat][1],
            "image": p["image"], "link": p["link"], "store": store_of(p["link"]),
            "caption": (p.get("caption") or "").strip(),
            "order": p.get("order") if isinstance(p.get("order"), (int, float)) else 1e9, "i": i,
        })
    out.sort(key=lambda x: (x["order"], x["i"]))
    return out


# ---------- page pieces ----------
LOGO_SVG = ('<svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true"><rect x="2" y="24" width="30" height="3" rx="1.5" fill="#F0A35E"/>'
            '<rect x="5" y="10" width="9" height="13" rx="2" fill="none" stroke="#fff" stroke-width="2"/>'
            '<rect x="17" y="6" width="11" height="17" rx="2" fill="none" stroke="#fff" stroke-width="2"/>'
            '<path d="M19 14l2.5 2.5L26 12" fill="none" stroke="#F0A35E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')
SEARCH_SVG = ('<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" '
              'stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>')
CHEV = ('<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="#A04A12" stroke-width="2" '
        'stroke-linecap="round"><path d="M9 6l6 6-6 6"/></svg>')


def head(title, desc, path, extra_ld=None, og_image=None):
    url = SITE_URL + path
    ld = ""
    if extra_ld:
        ld = '<script type="application/ld+json">' + json.dumps(extra_ld, ensure_ascii=False).replace("</", "<\\/") + "</script>"
    img = f'<meta property="og:image" content="{e(og_image)}">' if og_image else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="impact-site-verification" value="f5ba2004-9dde-479b-bfbf-44d7ba98395e">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Smart Shelf Picks">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
{img}
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/logo.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-5WY7BZPJ1E"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-5WY7BZPJ1E');</script>
{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
<div class="wrap top-in">
<a class="brand" href="/">{LOGO_SVG}<span>Smart Shelf <b>Picks</b></span></a>
<nav class="mainnav" aria-label="Main">
<a href="/categories/">Categories</a>
<a href="/category/deals-steals/">Deals</a>
<a href="/about/">About</a>
<a href="/contact/">Contact</a>
</nav>
<form class="search" role="search" action="/search/" method="get">
<label for="q" class="sr">Search picks</label>
<input id="q" name="q" type="search" placeholder="Search picks, e.g. heater">
<button type="submit" aria-label="Search">{SEARCH_SVG}</button>
</form>
</div>
</header>
"""


def foot():
    year = datetime.now(timezone.utc).year
    return f"""<footer class="foot">
<div class="wrap foot-in">
<div class="foot-brand">
<div class="fb-name">Smart Shelf <b>Picks</b></div>
<p>A small, independent U.S. shopping guide. We share the products and deals we think are worth your time and money.</p>
</div>
<div class="foot-col">
<div class="fc-h">Site</div>
<a href="/about/">About us</a>
<a href="/contact/">Contact us</a>
<a href="/privacy/">Privacy Policy</a>
<a href="/categories/">All categories</a>
</div>
<div class="foot-col">
<div class="fc-h">Follow @smartshelfpicks</div>
<a href="https://www.pinterest.com/smartshelfpicks/" rel="me noopener" target="_blank">Pinterest</a>
<a href="https://www.instagram.com/smartshelfpicks/" rel="me noopener" target="_blank">Instagram</a>
<a href="https://www.facebook.com/smartshelfpicks" rel="me noopener" target="_blank">Facebook</a>
</div>
</div>
<div class="wrap foot-note">Affiliate disclosure: some links are affiliate links. We may earn a small commission if you buy through them, at no extra cost to you. Prices change often; the retailer's page always shows today's price. &copy; {year} Smart Shelf Picks</div>
</footer>
</body>
</html>
"""


def card(p):
    badge = f'<span class="badge">{e(p["badge"])}</span>' if p["badge"] else ""
    return f"""<article class="card">
<a class="card-img" href="/p/{p['slug']}/">{badge}<img src="{e(p['image'])}" alt="{e(p['name'])}" loading="lazy" decoding="async" referrerpolicy="no-referrer"></a>
<div class="card-body">
<a class="card-cat" href="/category/{p['cat_slug']}/">{e(p['cat'])}</a>
<h3><a href="/p/{p['slug']}/">{e(p['name'])}</a></h3>
<p>{e(p['caption'])}</p>
<a class="btn" href="{e(p['link'])}" rel="sponsored nofollow noopener" target="_blank">See today's price at {e(p['store'])}</a>
</div>
</article>"""


def grid(items):
    return '<div class="grid">\n' + "\n".join(card(p) for p in items) + "\n</div>"


def faq_html(faq):
    out = []
    for i, (q, a) in enumerate(faq):
        out.append(f'<details{" open" if i == 0 else ""}><summary>{e(q)}</summary><p>{e(a)}</p></details>')
    return "\n".join(out)


def crumbs(parts):
    links = []
    for i, (name, href) in enumerate(parts):
        links.append(f'<a href="{href}">{e(name)}</a>' if href and i < len(parts) - 1 else f"<span>{e(name)}</span>")
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE_URL + (h or "")} for i, (n, h) in enumerate(parts)]}
    return '<nav class="crumbs" aria-label="Breadcrumb">' + " / ".join(links) + "</nav>", ld


def write(path, text):
    full = os.path.join(OUT, path.lstrip("/"))
    if full.endswith("/"):
        full += "index.html"
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)


# ---------- pages ----------
def build(products, copy):
    pages = []
    by_cat = {c[0]: [p for p in products if p["cat"] == c[0]] for c in CATEGORIES}
    deals = [p for p in products if p["badge"] or p["cat"] == "Deals & Steals"]
    latest = [p for p in products if not (p["badge"] or p["cat"] == "Deals & Steals")]
    org_ld = {"@context": "https://schema.org", "@type": "Organization", "name": "Smart Shelf Picks", "url": SITE_URL,
              "logo": SITE_URL + "/assets/logo.svg", "email": "smartshelfpicks@gmail.com",
              "sameAs": ["https://www.pinterest.com/smartshelfpicks/", "https://www.instagram.com/smartshelfpicks/",
                         "https://www.facebook.com/smartshelfpicks"]}

    # Home
    tiles = [("Deals & Steals", "Refurbished tech & holiday decor"), ("Gift Ideas", "For music lovers & more"),
             ("Home & Decor", "Stay cozy this winter"), ("Pet Picks", "Comfy beds & treats")]
    tile_html = "\n".join(f'<a class="tile" href="/category/{CAT_BY_NAME[n][1]}/"><span class="t-name">{e(n)}</span><span class="t-note">{e(note)}</span></a>' for n, note in tiles)
    cats_html = "\n".join(f'<a class="catlink" href="/category/{s}/">{e(n)}{CHEV}</a>' for n, s, _ in CATEGORIES)
    home = head("Smart Shelf Picks | Useful finds and real deals, picked for you",
                "Hand-picked products and real deals across home, kitchen, tech, fitness, travel, gifts, kids and pets. Fresh picks every week.",
                "/", org_ld, products[0]["image"] if products else None)
    home += f"""<section class="hero">
<div class="wrap hero-in">
<div class="hero-copy">
<h1>Useful finds, picked<br>and checked for you.</h1>
<p>Fresh picks are added every week. Tap any product to see today's price and details on the retailer's site.</p>
<div class="hero-btns"><a class="btn-orange" href="#latest">Browse latest picks</a><a class="btn-ghost" href="#deals">Deals</a></div>
</div>
<div class="tiles">{tile_html}</div>
</div>
</section>
<main id="main" class="wrap">
<section class="sec" aria-labelledby="cats-h">
<h2 id="cats-h">Shop by category</h2>
<div class="catgrid">{cats_html}</div>
</section>
<section id="latest" class="sec" aria-labelledby="latest-h">
<div class="sec-head"><h2 id="latest-h">Latest picks</h2><span class="muted">Updated automatically from our product list</span></div>
{grid(latest[:12])}
</section>
{f'''<section id="deals" class="deals" aria-labelledby="deals-h">
<h2 id="deals-h">Deals worth a look</h2>
<p>Certified refurbished and seasonal deals. Prices move fast, so check before you buy.</p>
{grid(deals[:8])}
</section>''' if deals else ''}
</main>
"""
    write("/", home + foot())
    pages.append("/")

    # Categories index
    ci = head("All categories | Smart Shelf Picks", "Browse every Smart Shelf Picks category, from kitchen finds to pet picks.", "/categories/")
    ci += f'<main id="main" class="wrap page">\n{crumbs([("Home", "/"), ("Categories", "/categories/")])[0]}\n<h1>All categories</h1>\n<div class="catgrid">' + \
          "\n".join(f'<a class="catlink" href="/category/{s}/">{e(n)} <span class="muted">({len(by_cat[n])})</span>{CHEV}</a>' for n, s, _ in CATEGORIES) + "</div>\n</main>\n"
    write("/categories/", ci + foot())
    pages.append("/categories/")

    # Category pages
    for name, slug, intro in CATEGORIES:
        items = by_cat[name]
        if slug == "deals-steals":
            items = deals
        c = copy.get("pages", {}).get(slug, {})
        cr, cr_ld = crumbs([("Home", "/"), (name, f"/category/{slug}/")])
        ld = [cr_ld, {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": f"{SITE_URL}/p/{p['slug']}/", "name": p["name"]} for i, p in enumerate(items)]}]
        if c.get("faq"):
            ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in c["faq"]]})
        pg = head(f"{name} | Smart Shelf Picks", f"{intro} Hand-picked by Smart Shelf Picks.", f"/category/{slug}/", ld,
                  items[0]["image"] if items else None)
        more = "\n".join(f'<a class="pill" href="/category/{s}/">{e(n)}</a>' for n, s, _ in CATEGORIES if s != slug)
        guide = ""
        if c.get("guide") or c.get("faq"):
            guide = f"""<section class="guide">
<div class="g-col"><h2>{e(c.get('title', 'How we choose'))}</h2><p>{e(c.get('guide', ''))}</p></div>
<div class="g-col"><h2>Common questions</h2>{faq_html(c.get('faq', []))}</div>
</section>"""
        body = grid(items) if items else '<p class="empty">New picks for this category are on the way. Check back soon.</p>'
        pg += f"""<main id="main" class="wrap page">
{cr}
<div class="intro"><h1>{e(name)}</h1><p>{e(intro)} Fresh picks are added every week. Tap any product to see today's price on the retailer's site.</p></div>
{body}
{guide}
<section class="more"><h2>More categories</h2><div class="pills">{more}</div></section>
</main>
"""
        write(f"/category/{slug}/", pg + foot())
        pages.append(f"/category/{slug}/")

    # Product pages
    for p in products:
        cr, cr_ld = crumbs([("Home", "/"), (p["cat"], f"/category/{p['cat_slug']}/"), (p["name"], f"/p/{p['slug']}/")])
        related = [x for x in products if x["cat"] == p["cat"] and x is not p][:3]
        if len(related) < 3:
            related += [x for x in products if x is not p and x not in related][: 3 - len(related)]
        desc = p["caption"] or f"{p['name']}, picked by Smart Shelf Picks."
        badge = f'<span class="badge inline">{e(p["badge"])}</span> ' if p["badge"] else ""
        pin = ("https://www.pinterest.com/pin/create/button/?" + urllib.parse.urlencode(
            {"url": f"{SITE_URL}/p/{p['slug']}/", "media": p["image"], "description": p["name"]}))
        pg = head(f"{p['name']} | Smart Shelf Picks", desc[:300], f"/p/{p['slug']}/", cr_ld, p["image"])
        pg += f"""<main id="main" class="wrap page">
{cr}
<section class="prod">
<div class="prod-img"><img src="{e(p['image'])}" alt="{e(p['name'])}" referrerpolicy="no-referrer"></div>
<div class="prod-info">
<div class="kicker">{badge}{e(p['cat'])} · Sold by {e(p['store'])}</div>
<h1>{e(p['name'])}</h1>
<p class="lead">{e(p['caption'])}</p>
<a class="btn big" href="{e(p['link'])}" rel="sponsored nofollow noopener" target="_blank">See today's price at {e(p['store'])}</a>
<p class="small">Opens the retailer's site. This is an affiliate link: we may earn a small commission at no extra cost to you. Prices and stock change often.</p>
<div class="share"><a class="btn-line" href="{e(pin)}" target="_blank" rel="noopener">Save on Pinterest</a><button class="btn-line" type="button" data-share>Share</button></div>
</div>
</section>
<section class="sec"><h2>You might also like</h2>{grid(related)}</section>
</main>
<script>document.querySelectorAll('[data-share]').forEach(function(b){{b.addEventListener('click',function(){{var u=location.href;if(navigator.share){{navigator.share({{title:document.title,url:u}}).catch(function(){{}});}}else if(navigator.clipboard){{navigator.clipboard.writeText(u);b.textContent='Link copied';}}}});}});</script>
"""
        write(f"/p/{p['slug']}/", pg + foot())
        pages.append(f"/p/{p['slug']}/")

    # About
    ab = copy.get("about", {})
    paras = "".join(f"<p>{e(x)}</p>" for x in ab.get("paras", []))
    pg = head("About | Smart Shelf Picks", "Who we are and how we choose the products and deals we share.", "/about/", org_ld)
    pg += f'<main id="main" class="wrap page narrow">\n{crumbs([("Home", "/"), ("About", "/about/")])[0]}\n<h1>{e(ab.get("title", "About Smart Shelf Picks"))}</h1>\n<div class="prose">{paras}</div>\n</main>\n'
    write("/about/", pg + foot())
    pages.append("/about/")

    # Privacy
    pv = [
        ("", "Smart Shelf Picks (\"we\") runs this website and our Pinterest, Facebook and Instagram accounts. This policy explains what information is collected when you visit."),
        ("What we collect", "We don't ask you to create an account, and we don't collect your name, email or payment details unless you send us a message through our contact form. We use Google Analytics to see anonymous visit statistics, such as which pages are popular and roughly which country visits come from. Google may use cookies for this. You can opt out with the Google Analytics Opt-out Browser Add-on."),
        ("Affiliate links", "Some links on this site are affiliate links (eBay Partner Network, Impact, CJ, Rakuten and others). If you buy through one, we may earn a small commission at no extra cost to you. When you click, the retailer or network may set its own cookies to track the referral. Their privacy policies apply on their sites."),
        ("Contact form", "If you send us a message through our contact form, we receive the name, email address and message you enter. We keep them in our private records and use them only to reply to you. We never sell or share them."),
        ("Social media posting", "We use the Meta (Facebook/Instagram) and Pinterest platforms only to publish posts to our own accounts. Our app does not collect, store or share data about other users."),
        ("Data deletion", "Apart from contact form messages, we don't store personal data about visitors or social media users. If you think we have any information about you and want it removed, email us and we'll delete it."),
        ("Children", "This site is not directed at children under 13."),
        ("Contact", "smartshelfpicks@gmail.com"),
    ]
    body = "".join((f"<h2>{e(h)}</h2>" if h else "") + f"<p>{e(t)}</p>" for h, t in pv)
    pg = head("Privacy Policy | Smart Shelf Picks", "How Smart Shelf Picks handles visitor information, cookies, affiliate links and contact form messages.", "/privacy/")
    pg += f'<main id="main" class="wrap page narrow">\n{crumbs([("Home", "/"), ("Privacy Policy", "/privacy/")])[0]}\n<h1>Privacy Policy</h1>\n<p class="muted">Last updated: November 19, 2026</p>\n<div class="prose">{body}</div>\n</main>\n'
    write("/privacy/", pg + foot())
    pages.append("/privacy/")

    # Contact
    topics = ["A question about a pick", "Suggest a product", "Brand or partnership", "Something else"]
    opts = "".join(f"<option>{e(t)}</option>" for t in topics)
    pg = head("Contact | Smart Shelf Picks", "Questions, product suggestions or partnership ideas? Send Smart Shelf Picks a message.", "/contact/")
    pg += f"""<main id="main" class="wrap page">
{crumbs([("Home", "/"), ("Contact", "/contact/")])[0]}
<section class="contact">
<div class="contact-copy">
<h1>Get in touch</h1>
<p class="lead">Have a question about a pick, a product you'd like us to look at, or a brand partnership idea? Send us a note and we'll reply to the email you enter.</p>
<p>Questions about an order, shipping or a return go to the retailer you bought from. They have your order details.</p>
</div>
<form class="ssp-form" id="contact-form" action="{e(SCRIPT_URL)}" method="post" novalidate>
<h2>Send us a message</h2>
<div class="ssp-row">
<div class="ssp-field"><label for="name">Your name</label><input id="name" name="name" type="text" autocomplete="name" maxlength="100"></div>
<div class="ssp-field"><label for="email">Email</label><input id="email" name="email" type="email" autocomplete="email" required maxlength="200"></div>
</div>
<div class="ssp-field"><label for="topic">What's it about?</label><select id="topic" name="topic">{opts}</select></div>
<div class="ssp-field"><label for="message">Message</label><textarea id="message" name="message" rows="6" required maxlength="4000"></textarea></div>
<div class="ssp-hp" aria-hidden="true"><label for="website">Website</label><input id="website" name="website" type="text" tabindex="-1" autocomplete="off"></div>
<input type="hidden" name="source" value="GitHub site">
<button type="submit">Send message</button>
<p id="ssp-status" class="ssp-status" role="status" aria-live="polite"></p>
<p class="ssp-note">We only use your email to reply to you. See our <a href="/privacy/">Privacy Policy</a>.</p>
</form>
</section>
</main>
<script src="/assets/contact.js" defer></script>
"""
    write("/contact/", pg + foot())
    pages.append("/contact/")

    # Search (runs in the browser over products.json)
    pg = head("Search | Smart Shelf Picks", "Search all Smart Shelf Picks products.", "/search/")
    pg += f"""<main id="main" class="wrap page">
{crumbs([("Home", "/"), ("Search", "/search/")])[0]}
<h1 id="s-title">Search picks</h1>
<div id="s-results" class="grid"></div>
<p id="s-empty" class="empty" hidden>No picks match that yet. Try another word, or <a href="/categories/">browse all categories</a>.</p>
</main>
<script src="/assets/search.js" defer></script>
"""
    write("/search/", pg.replace('<meta name="description"', '<meta name="robots" content="noindex"><meta name="description"', 1) + foot())

    # 404
    pg = head("Page not found | Smart Shelf Picks", "That page isn't here.", "/404.html")
    pg += '<main id="main" class="wrap page narrow"><h1>That page isn\'t here</h1><p class="lead">The pick may have sold out or moved. <a href="/">Go to the home page</a> or <a href="/categories/">browse all categories</a>.</p></main>\n'
    write("/404.html", pg + foot())

    # Data for search, sitemap, robots
    write("/products.json", json.dumps([{k: p[k] for k in ("name", "slug", "cat", "cat_slug", "image", "link", "store", "caption", "badge")} for p in products], ensure_ascii=False))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"<url><loc>{SITE_URL}{u}</loc><lastmod>{today}</lastmod></url>" for u in pages]
    sm.append("</urlset>")
    write("/sitemap.xml", "\n".join(sm) + "\n")
    write("/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    write("/.nojekyll", "")
    return pages


def main():
    feed = load_feed()
    products = prepare(feed.get("products", []))
    if not products:
        sys.exit("No products in the feed; keeping the current site.")
    with open(os.path.join(ROOT, "site_copy.json"), encoding="utf-8") as f:
        copy = json.load(f)
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets"))
    for name in ("style.css", "contact.js", "search.js", "logo.svg"):
        shutil.copy(os.path.join(ROOT, name), os.path.join(OUT, "assets", name))
    pages = build(products, copy)
    print(f"Built {len(pages)} pages from {len(products)} products into {OUT}/")


if __name__ == "__main__":
    main()
