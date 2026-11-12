#!/usr/bin/env python3
"""
Импорт экспорта WordPress (WXR, «Инструменты → Экспорт») в JSON-контент сайта.

  python3 tools/import_wxr.py WordPress.2026-11-12.xml

Создаёт:
  content/site.json              — меню, рубрики
  content/posts/ГГГГ/<slug>.json — записи
  content/pages/<slug>.json      — страницы
  content/media.txt              — список нужных медиафайлов (для tools/fetch_media.py)

НЕ переносятся: пожертвования (leyka_donation — личные данные жертвователей),
комментарии, авторы, служебные записи WordPress.
"""
import html, json, os, re, shutil, sys, urllib.parse
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "content")
NS = {"wp": "http://wordpress.org/export/1.2/", "content": "http://purl.org/rss/1.0/modules/content/",
      "excerpt": "http://wordpress.org/export/1.2/excerpt/"}
SITE_RE = r"(?:https?:)?//(?:www\.)?helpautism\.ru"
SKIP_PAGES = {"tester", "thank-you-for-your-donation", "sorry-donation-failure"}


def g(it, k):
    return it.findtext(k, namespaces=NS) or ""


def meta(it):
    return {g(m, "wp:meta_key"): g(m, "wp:meta_value") for m in it.findall("wp:postmeta", NS)}


def autop(text):
    """Упрощённый wpautop для записей из старого редактора (без <p>)."""
    if re.search(r"<!-- wp:|<p[ >]", text):
        return text
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip())
    out = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if re.match(r"(?is)^<(h\d|ul|ol|table|blockquote|div|figure|iframe|pre|hr)", b):
            out.append(b)
        else:
            out.append("<p>" + b.replace("\n", "<br>\n") + "</p>")
    return "\n".join(out)


def clean_content(c):
    c = re.sub(r"<!--\s*/?wp:[^>]*?-->", "", c)                     # разметка блоков Gutenberg
    c = autop(c)
    # шорткоды
    c = re.sub(r'\[contact-form-7 id="(\d+)"[^\]]*\]', r'<div class="ha-form" data-form="\1"></div>', c)
    c = re.sub(r"\[(masterslider|easingslider|joomgallery)[^\]]*\]", '<div class="ha-gallery-slot"></div>', c)
    c = re.sub(r"\[leyka_campaign_form[^\]]*\]", '<div class="ha-donate-slot"></div>', c)
    c = re.sub(r"\[table id=(\d+)\s*/\]", r'<div class="ha-table" data-table="\1"></div>', c)
    c = re.sub(r"\[embed\](.*?)\[/embed\]", lambda m: embed(m.group(1).strip()), c, flags=re.S)
    c = re.sub(r"\[video[^\]]*?(?:mp4|src)=\"([^\"]+)\"[^\]]*\](?:\[/video\])?", r'<video controls preload="metadata" src="\1"></video>', c)
    c = re.sub(r"\[(?:h?accordion)\s+title=\"([^\"]*)\"[^\]]*\]", r'<details class="ha-acc"><summary>\1</summary>', c)
    c = re.sub(r"\[/(?:h?accordion)\]", "</details>", c)
    c = re.sub(r"\[/?(?:h?accordions|google_map_easy|my_calendar|add_eventon|video-\d+)[^\]]*\]", "", c)
    # ссылки на сайт -> от корня
    c = re.sub(SITE_RE + r"(/[^\s\"'<>)]*)?", lambda m: m.group(1) or "/", c)
    c = re.sub(r"\n{3,}", "\n\n", c).strip()
    return c


def embed(url):
    u = html.unescape(url)
    y = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([\w-]{11})", u)
    if y:
        return f'<div class="ha-video"><iframe src="https://www.youtube-nocookie.com/embed/{y.group(1)}" allowfullscreen loading="lazy"></iframe></div>'
    if "vk.com/video" in u or "vkvideo.ru" in u:
        return f'<p><a href="{html.escape(u)}" target="_blank" rel="noopener">Смотреть видео</a></p>'
    return f'<p><a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(u)}</a></p>'


def text_excerpt(c, n=220):
    t = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style|figure|details)[^>]*>.*?</\1>", " ", c)))
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:n].rsplit(" ", 1)[0] + "…") if len(t) > n else t


def local_upload(url):
    m = re.match(SITE_RE + r"(/wp-content/uploads/[^\s\"'<>?#]+)", url or "")
    return urllib.parse.unquote(m.group(1)) if m else ""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "WordPress.xml")
    data = open(src, "rb").read().decode("utf-8", "replace")
    data = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", data)
    root = ET.fromstring(data)
    ch = root.find("channel")
    items = ch.findall("item")

    # рубрики
    cats = {}
    for c in ch.findall("wp:category", NS):
        cats[g(c, "wp:category_nicename")] = {"id": g(c, "wp:term_id"), "name": html.unescape(g(c, "wp:cat_name")), "parent": g(c, "wp:category_parent")}
    def cat_path(slug, seen=()):
        c = cats.get(slug)
        if not c or slug in seen:
            return slug
        return (cat_path(c["parent"], seen + (slug,)) + "/" + slug) if c["parent"] else slug
    for s, c in cats.items():
        c["path"] = "/category/" + cat_path(s) + "/"
    cat_by_id = {c["id"]: s for s, c in cats.items()}

    att = {}
    att_by_parent = {}
    for it in items:
        if g(it, "wp:post_type") != "attachment":
            continue
        a = {"id": g(it, "wp:post_id"), "url": local_upload(g(it, "wp:attachment_url")), "parent": g(it, "wp:post_parent"),
             "order": int(g(it, "wp:menu_order") or 0), "date": g(it, "wp:post_date")}
        att[a["id"]] = a
        att_by_parent.setdefault(a["parent"], []).append(a)

    if os.path.isdir(OUT):
        for sub in ("posts", "pages"):
            shutil.rmtree(os.path.join(OUT, sub), ignore_errors=True)
    os.makedirs(OUT, exist_ok=True)
    media = set()
    n_posts = n_pages = 0
    by_id = {g(it, "wp:post_id"): it for it in items}

    for it in items:
        t = g(it, "wp:post_type")
        if t not in ("post", "page") or g(it, "wp:status") != "publish":
            continue
        slug = urllib.parse.unquote(g(it, "wp:post_name"))
        if t == "page" and slug in SKIP_PAGES:
            continue
        raw = g(it, "content:encoded")
        content = clean_content(raw)
        m = meta(it)
        thumb = att.get(m.get("_thumbnail_id", ""), {}).get("url", "")
        # галерея: картинки, прикреплённые к записи (masterslider/easingslider в экспорт не попадают)
        gallery = []
        if "ha-gallery-slot" in content:
            for a in sorted(att_by_parent.get(g(it, "wp:post_id"), []), key=lambda a: (a["order"], a["date"])):
                if re.search(r"\.(jpe?g|png|gif|webp)$", a["url"], re.I) and a["url"] not in content:
                    gallery.append(a["url"])
        path = urllib.parse.unquote(urllib.parse.urlsplit(g(it, "link")).path) or f"/{slug}/"
        doc = {
            "id": int(g(it, "wp:post_id")), "type": t, "slug": slug, "path": path,
            "title": html.unescape(g(it, "title")).strip(),
            "date": g(it, "wp:post_date")[:10], "modified": g(it, "wp:post_modified")[:10],
            "categories": [c.get("nicename") for c in it.findall("category") if c.get("domain") == "category"],
            "thumbnail": thumb, "gallery": gallery,
            "excerpt": html.unescape(g(it, "excerpt:encoded")).strip() or text_excerpt(content),
            "content": content,
        }
        if t == "page":
            doc["parent"] = urllib.parse.unquote(g(by_id[g(it, "wp:post_parent")], "wp:post_name")) if g(it, "wp:post_parent") in by_id else ""
        for u in re.findall(r"(/wp-content/uploads/[^\s\"'<>)?#]+)", content):
            media.add(urllib.parse.unquote(u))
        media.update(x for x in [thumb] + gallery if x)
        if t == "post":
            d = os.path.join(OUT, "posts", doc["date"][:4]); n_posts += 1
        else:
            d = os.path.join(OUT, "pages"); n_pages += 1
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, slug + ".json"), "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)

    # меню «Верхнее меню»
    menu_items = []
    for it in items:
        if g(it, "wp:post_type") != "nav_menu_item":
            continue
        if not any(c.get("domain") == "nav_menu" for c in it.findall("category")):
            continue
        m = meta(it)
        typ, obj, oid = m.get("_menu_item_type"), m.get("_menu_item_object"), m.get("_menu_item_object_id")
        title, url = html.unescape(g(it, "title")).strip(), m.get("_menu_item_url", "")
        if typ == "taxonomy" and obj == "category" and oid in cat_by_id:
            s = cat_by_id[oid]; url = cats[s]["path"]; title = title or cats[s]["name"]
        elif typ == "post_type" and oid in by_id:
            o = by_id[oid]; url = urllib.parse.unquote(urllib.parse.urlsplit(g(o, "link")).path); title = title or html.unescape(g(o, "title"))
        url = re.sub(SITE_RE, "", url) or "/"
        menu_items.append({"id": g(it, "wp:post_id"), "parent": m.get("_menu_item_menu_item_parent", "0"), "order": int(g(it, "wp:menu_order") or 0), "title": title, "url": url})
    def tree(pid):
        return [{"title": x["title"], "url": x["url"], "children": tree(x["id"])} for x in sorted(menu_items, key=lambda x: x["order"]) if x["parent"] == pid]
    menu = tree("0")

    # таблицы TablePress
    tables = {}
    for it in items:
        if g(it, "wp:post_type") == "tablepress_table":
            try:
                tables[g(it, "wp:post_id")] = json.loads(g(it, "content:encoded"))
            except Exception:
                pass
    tp_map = {}
    for it in items:  # id таблицы в шорткоде -> id записи
        if g(it, "wp:post_type") == "tablepress_table":
            tp_map[g(it, "wp:post_id")] = g(it, "wp:post_id")

    site = {"title": html.unescape(ch.findtext("title") or ""), "menu": menu,
            "categories": {s: {"name": c["name"], "parent": c["parent"], "path": c["path"]} for s, c in cats.items()},
            "tables": tables}
    with open(os.path.join(OUT, "site.json"), "w", encoding="utf-8") as f:
        json.dump(site, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "media.txt"), "w") as f:
        f.write("\n".join(sorted(media)) + "\n")
    print(f"Записей: {n_posts}, страниц: {n_pages}, пунктов меню: {len(menu_items)}, медиафайлов: {len(media)}")


if __name__ == "__main__":
    main()
