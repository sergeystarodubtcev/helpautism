#!/usr/bin/env python3
"""
Сборка сайта «Сокровенный человек» (innermost.helpautism.ru).

Контент — sites/innermost/content (меняется из общей админки helpautism.ru/admin/, профиль «Сокровенный человек»):
  settings.json            — тексты главной, проекты, реквизиты, контакты, цвета, соцсети
  posts/ГГГГ/*.json         — новости
  pages/*.json              — страницы
Файлы — sites/innermost/media (картинки из админки попадают в media/uploads/ГГГГ/ММ/).

Результат — папка site-innermost/. Список записей для админки дополнительно кладётся
в site/data/sites/innermost.json (если основной сайт уже собран).
"""
import glob, html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sites", "innermost")
OUT = os.path.join(ROOT, "site-innermost")
MAIN_OUT = os.path.join(ROOT, "site")
SITE_URL = "https://innermost.helpautism.ru"
ADMIN_URL = "https://helpautism.ru/admin/?site=innermost"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from build_site import SOCIAL_ICONS  # noqa: E402  — те же значки, что на основном сайте

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
E = lambda s: html.escape(str(s or ""), quote=True)


def load(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def ru_date(d):
    try:
        y, m, dd = d.split("-")
        return f"{int(dd)} {MONTHS[int(m) - 1]} {y}"
    except Exception:
        return d or ""


def text_excerpt(h, n=180):
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h or ""))).strip()
    return (t[:n].rsplit(" ", 1)[0] + "…") if len(t) > n else t


def safe_url(u):
    u = str(u or "").strip()
    return u if re.match(r"^(https://|/|#|tel:|mailto:)", u) else ""


S = load(os.path.join(SRC, "content", "settings.json"), {}) or {}
POSTS = sorted((d for d in (load(p) for p in glob.glob(os.path.join(SRC, "content", "posts", "*", "*.json"))) if d and d.get("title")),
               key=lambda d: d.get("date", ""), reverse=True)
PAGES = [d for d in (load(p) for p in glob.glob(os.path.join(SRC, "content", "pages", "*.json"))) if d and d.get("title")]
for p in POSTS:
    p.setdefault("path", "/{0}/{1}/{2}/{3}/".format(*p["date"].split("-"), p["slug"]))
for p in PAGES:
    p.setdefault("path", f"/{p['slug']}/")


def theme_style():
    c = S.get("colors", {})
    ok = lambda v: bool(re.match(r"^#[0-9a-fA-F]{6}$", str(v or "")))
    v = "".join(f"--{k}:{c[k]};" for k in ("ink", "accent", "cta") if ok(c.get(k)))
    return f"<style id=\"ha-theme\">:root{{{v}}}</style>" if v else ""


def social_html():
    out = []
    for k, (title, svg) in SOCIAL_ICONS.items():
        url = safe_url((S.get("social") or {}).get(k))
        if url.startswith("https://"):
            out.append(f'<a href="{E(url)}" target="_blank" rel="noopener" title="{E(title)}" aria-label="{E(title)}">'
                       f'<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">{svg}</svg></a>')
    return f'<div class="soc">{"".join(out)}</div>' if out else ""


def help_href():
    u = safe_url((S.get("donate") or {}).get("url"))
    return (u, ' target="_blank" rel="noopener"') if u.startswith("https://") else ("/#help", "")


def tel(p):
    return "tel:" + re.sub(r"[^\d+]", "", p or "")


def layout(title, body, desc="", cls="", og_img=""):
    h = S.get("hero", {})
    full = f"{title} — {h.get('title', 'Сокровенный человек')}" if title else f"{h.get('title', '')} — {h.get('subtitle', '')}"
    desc = desc or h.get("text", "")
    hh, ht = help_href()
    c = S.get("contacts", {})
    docs = "".join(f'<li><a href="{E(safe_url(d.get("url")))}" target="_blank" rel="noopener">{E(d.get("title"))}</a></li>'
                   for d in c.get("docs", []) if safe_url(d.get("url")))
    nav = [("/#about", "О нас"), ("/#projects", "Наши проекты"), ("/novosti/", "Новости"), ("/#help", "Помочь"), ("/#contacts", "Контакты")]
    nav_html = "".join(f'<a href="{u}">{t}</a>' for u, t in nav)
    og = f'<meta property="og:image" content="{SITE_URL}{E(og_img or S.get("hero_image", ""))}">'
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(full)}</title>
<meta name="description" content="{E(desc)}">
<meta property="og:title" content="{E(full)}">
<meta property="og:description" content="{E(desc)}">
{og}
<meta name="theme-color" content="#ffffff">
<link rel="icon" href="/favicon.ico">
<link rel="stylesheet" href="/assets/fonts/fonts.css">
<link rel="stylesheet" href="/assets/style.css">
{theme_style()}
</head>
<body class="{cls}">
<div class="progress" aria-hidden="true"></div>
<header class="nav" id="top"><div class="wrap nav-in">
  <a class="logo" href="/" aria-label="{E(h.get('title'))} — на главную"><img src="/uploads/craftum/logo.png" alt="{E(h.get('title'))}" width="160" height="117"></a>
  <nav class="menu" id="menu">{nav_html}<a class="btn btn-cta menu-cta" href="{E(hh)}"{ht}>Я хочу помочь</a></nav>
  <a class="btn btn-cta nav-cta" href="{E(hh)}"{ht}>Я хочу помочь</a>
  <button class="burger" aria-label="Меню" aria-controls="menu" aria-expanded="false"><span></span><span></span></button>
</div></header>
<main>
{body}
</main>
<footer class="foot"><div class="wrap">
  <div class="foot-grid">
    <div><img class="foot-logo" src="/uploads/craftum/logo.png" alt="" width="140" height="102" loading="lazy"><p>{E(S.get('footer'))}</p>{social_html()}</div>
    <div><h4>Контакты</h4><p>{E(c.get('person'))}<br><a href="{E(tel(c.get('phone')))}">{E(c.get('phone'))}</a>{('<br><a href="mailto:' + E(c.get('email')) + '">' + E(c.get('email')) + '</a>') if c.get('email') else ''}</p></div>
    <div><h4>Документы</h4><ul>{docs}<li><a href="/politika-konfidencialnosti/">Политика конфиденциальности</a></li></ul></div>
  </div>
  <div class="foot-bottom"><span>© {E(c.get('org'))}{(' · ИНН ' + E(c.get('inn'))) if c.get('inn') else ''}</span><a href="#top" class="up">Наверх ↑</a></div>
</div></footer>
<div class="lb" hidden><img alt=""><button class="lb-x" aria-label="Закрыть">×</button></div>
<script src="/assets/site.js" defer></script>
</body>
</html>
"""


def news_card(p):
    img = p.get("thumbnail")
    pic = f'<img src="{E(img)}" alt="" loading="lazy">' if img else '<span class="ph"></span>'
    ex = p.get("excerpt") or text_excerpt(p.get("content"), 150)
    return (f'<a class="card news reveal" href="{E(p["path"])}"><span class="card-img">{pic}</span><span class="card-body">'
            f'<time datetime="{E(p["date"])}">{ru_date(p["date"])}</time><b>{E(p["title"])}</b><span class="ex">{E(ex)}</span>'
            f'<span class="more">Читать →</span></span></a>')


def home():
    h, a, hp, d, c = (S.get(k, {}) for k in ("hero", "about", "help", "donate", "contacts"))
    hh, ht = help_href()
    projects = "".join(
        f'<article class="proj reveal"><div class="proj-img">{("<img src=" + chr(34) + E(p.get("image")) + chr(34) + " alt=" + chr(34) + chr(34) + " loading=lazy>") if p.get("image") else ""}</div>'
        f'<h3>{E(p.get("title"))}</h3><p class="sub">{E(p.get("subtitle"))}</p>{("<p>" + E(p.get("text")) + "</p>") if p.get("text") else ""}</article>'
        for p in S.get("projects", []))
    items = "".join(f'<li class="reveal">{E(x)}</li>' for x in hp.get("items", []))
    req = "<br>".join(E(x) for x in str(d.get("requisites", "")).split("\n") if x.strip())
    qr = f'<img class="qr" src="{E(d.get("qr"))}" alt="QR-код для пожертвования" loading="lazy">' if d.get("qr") else ""
    pay = f'<a class="btn btn-cta btn-big" href="{E(d["url"])}" target="_blank" rel="noopener">Пожертвовать онлайн</a>' if safe_url(d.get("url")).startswith("https://") else ""
    docs = "".join(f'<a class="doc" href="{E(safe_url(x.get("url")))}" target="_blank" rel="noopener">'
                   f'<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M12 3v12m0 0-4.5-4.5M12 15l4.5-4.5M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>{E(x.get("title"))}</a>'
                   for x in c.get("docs", []) if safe_url(x.get("url")))
    hero_img = S.get("hero_image") or ""
    body = f"""
<section class="hero">
  <img class="shape s1" src="/uploads/craftum/shape-1.png" alt="" aria-hidden="true">
  <img class="shape s2" src="/uploads/craftum/shape-2.png" alt="" aria-hidden="true">
  <div class="wrap hero-grid">
    <div class="hero-text">
      <p class="eyebrow reveal">{E(h.get('subtitle'))}</p>
      <h1 class="reveal">{E(h.get('title'))}</h1>
      <p class="lead reveal">{E(h.get('text'))}</p>
      <div class="hero-btns reveal"><a class="btn btn-cta" href="{E(hh)}"{ht}>Я хочу помочь</a><a class="btn btn-ghost" href="#projects">Наши проекты</a></div>
    </div>
    <div class="hero-pic reveal">{('<img src="' + E(hero_img) + '" alt="">') if hero_img else ''}</div>
  </div>
</section>

<section class="sec" id="news"><div class="wrap">
  <div class="sec-head"><h2 class="reveal">Новости</h2><a class="link-all" href="/novosti/">Смотреть все →</a></div>
  <div class="grid3">{"".join(news_card(p) for p in POSTS[:3]) or '<p class="muted">Новостей пока нет.</p>'}</div>
</div></section>

<section class="sec" id="about"><div class="wrap">
  <div class="box about reveal">
    <span class="pill">{E(a.get('title') or 'О нас')}</span>
    <p class="about-text">{E(a.get('text'))}</p>
    <a class="btn btn-ink" href="#contacts">{E(a.get('button') or 'Присоединяйтесь к нашей команде')}</a>
  </div>
</div></section>

<section class="sec" id="projects"><div class="wrap">
  <div class="sec-head"><h2 class="reveal">Наши проекты</h2></div>
  <div class="grid2">{projects}</div>
</div></section>

<section class="sec" id="help"><div class="wrap">
  <div class="box help reveal">
    <div class="help-top">
      <div>
        <h2>{E(hp.get('title'))}</h2>
        <p class="lead">{E(hp.get('text'))}</p>
        <h3>Вы также можете помочь нам:</h3>
        <ul class="ways">{items}</ul>
      </div>
      <img class="heart" src="/uploads/craftum/heart.png" alt="" loading="lazy">
    </div>
    <div class="donate" id="donate">
      <div>
        <h3>{E(d.get('title') or 'Помощь Центру')}</h3>
        <p>{E(d.get('text'))}</p>
        <p class="req">{req}</p>
        <button class="btn btn-ghost btn-small copy" data-copy="{E(d.get('requisites'))}">Скопировать реквизиты</button>
        {pay}
      </div>
      {qr}
    </div>
  </div>
</div></section>

<section class="sec" id="contacts"><div class="wrap">
  <div class="box contacts reveal">
    <span class="pill pill-fill">Контактная информация</span>
    <div class="ct-grid">
      <div><p class="muted">{E(c.get('caption'))}</p><p class="person">{E(c.get('person'))}</p>
        <p><a class="phone" href="{E(tel(c.get('phone')))}">{E(c.get('phone'))}</a></p>
        {('<p><a href="mailto:' + E(c.get('email')) + '">' + E(c.get('email')) + '</a></p>') if c.get('email') else ''}</div>
      <div class="docs">{docs}<a class="btn btn-cta" href="{E(hh)}"{ht}>Я хочу помочь</a></div>
    </div>
    <p class="org">{E(c.get('org'))}{(' · ИНН ' + E(c.get('inn'))) if c.get('inn') else ''}</p>
  </div>
</div></section>
"""
    return layout("", body, cls="home")


def gallery_html(g):
    if not g:
        return ""
    return '<div class="gallery">' + "".join(f'<a href="{E(u)}" class="zoom"><img src="{E(u)}" alt="" loading="lazy"></a>' for u in g) + "</div>"


def post_page(p, kind="post"):
    cover = f'<figure class="post-cover"><img src="{E(p["thumbnail"])}" alt=""></figure>' if p.get("thumbnail") else ""
    meta = f'<time datetime="{E(p["date"])}">{ru_date(p["date"])}</time>' if kind == "post" else ""
    back = '<a class="back" href="/novosti/">← Все новости</a>' if kind == "post" else '<a class="back" href="/">← На главную</a>'
    more = ""
    if kind == "post":
        others = [x for x in POSTS if x is not p][:3]
        if others:
            more = f'<section class="sec"><div class="wrap"><div class="sec-head"><h2>Другие новости</h2></div><div class="grid3">{"".join(news_card(x) for x in others)}</div></div></section>'
    body = f"""<article class="post"><div class="wrap narrow">{back}{meta}<h1>{E(p['title'])}</h1>{cover}
<div class="content">{p.get('content', '')}</div>{gallery_html(p.get('gallery'))}</div></article>{more}"""
    return layout(p["title"], body, desc=p.get("excerpt") or text_excerpt(p.get("content")), cls="inner", og_img=p.get("thumbnail"))


def news_list():
    body = f"""<section class="sec page-top"><div class="wrap"><h1>Новости</h1>
<div class="grid3">{"".join(news_card(p) for p in POSTS) or '<p class="muted">Новостей пока нет.</p>'}</div></div></section>"""
    return layout("Новости", body, cls="inner")


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(SRC, "media"), OUT, dirs_exist_ok=True)
    shutil.copytree(os.path.join(SRC, "assets"), os.path.join(OUT, "assets"), dirs_exist_ok=True)
    shutil.copytree(os.path.join(ROOT, "assets", "fonts"), os.path.join(OUT, "assets", "fonts"), dirs_exist_ok=True)
    write(os.path.join(OUT, "index.html"), home())
    write(os.path.join(OUT, "novosti", "index.html"), news_list())
    for p in POSTS:
        write(os.path.join(OUT, p["path"].strip("/"), "index.html"), post_page(p))
    for p in PAGES:
        write(os.path.join(OUT, p["path"].strip("/"), "index.html"), post_page(p, "page"))
    write(os.path.join(OUT, "404.html"), layout("Страница не найдена", '<section class="sec page-top"><div class="wrap narrow"><h1>Страница не найдена</h1>'
          '<p>Возможно, её перенесли. Начните с <a href="/">главной</a> или посмотрите <a href="/novosti/">новости</a>.</p></div></section>', cls="inner"))
    # вход в админку — общая админка на helpautism.ru, профиль «Сокровенный человек»
    write(os.path.join(OUT, "admin", "index.html"), f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">'
          f'<meta http-equiv="refresh" content="0;url={ADMIN_URL}"><a href="{ADMIN_URL}">Админка</a>')
    urls = ["/", "/novosti/"] + [p["path"] for p in POSTS + PAGES]
    write(os.path.join(OUT, "sitemap.xml"), '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"<url><loc>{SITE_URL}{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    write(os.path.join(OUT, "robots.txt"), f"User-agent: *\nDisallow: /admin/\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    rel = lambda p: os.path.relpath(p, ROOT).replace(os.sep, "/")
    idx = {"posts": [{"file": rel(f), "title": d["title"], "date": d.get("date", ""), "path": d.get("path", ""), "categories": []}
                     for f in glob.glob(os.path.join(SRC, "content", "posts", "*", "*.json")) for d in [load(f)] if d],
           "pages": [{"file": rel(f), "title": d["title"], "date": d.get("date", ""), "path": d.get("path", ""), "categories": []}
                     for f in glob.glob(os.path.join(SRC, "content", "pages", "*.json")) for d in [load(f)] if d],
           "categories": {}}
    for p in idx["posts"] + idx["pages"]:
        p["path"] = p["path"] or ""
    data = json.dumps(idx, ensure_ascii=False)
    write(os.path.join(OUT, "data", "admin.json"), data)
    if os.path.isdir(MAIN_OUT):
        write(os.path.join(MAIN_OUT, "data", "sites", "innermost.json"), data)
        shutil.copy2(os.path.join(SRC, "media", "uploads", "craftum", "logo.png"), os.path.join(MAIN_OUT, "data", "sites", "innermost-logo.png"))
    print(f"innermost: {len(POSTS)} новостей, {len(PAGES)} страниц -> {OUT}")


if __name__ == "__main__":
    main()
