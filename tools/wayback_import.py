#!/usr/bin/env python3
"""
Восстановление контента helpautism.ru из веб-архива (web.archive.org).

Запуск (на своём компьютере, нужен только Python 3.8+):
    python3 tools/wayback_import.py

Что делает:
  1. Получает из архива список всех сохранённых страниц сайта.
  2. Для каждой записи WordPress (/ГГГГ/ММ/ДД/slug/) и для страниц
     скачивает последний сохранённый снимок.
  3. Достаёт заголовок, дату, текст (.entry-content) и картинки.
  4. Картинки кладёт в assets/uploads/, текст записывает в data/news.json
     (статьи) и data/pages.json (прочие страницы).

Уже восстановленные записи (restored: true) повторно не скачиваются.
Ключи: --limit N (обработать не больше N записей), --delay СЕК.
"""
import argparse, hashlib, html, json, os, re, sys, time, urllib.parse, urllib.request
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "helpautism.ru"
UA = "helpautism-restore/1.0"
POST_RE = re.compile(r"^/(\d{4})/(\d{2})/(\d{2})/([^/]+)/?$")
SKIP_RE = re.compile(r"/(wp-|feed|tag/|category/|author/|page/\d|comment|xmlrpc|\?|amp/?$)", re.I)


def get(url, binary=False, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                return data if binary else data.decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1:
                print(f"  ! не удалось: {url} ({e})")
                return None
            time.sleep(2 ** (i + 1))


def cdx():
    q = urllib.parse.urlencode({
        "url": DOMAIN + "/*", "output": "json", "fl": "timestamp,original,mimetype,statuscode",
        "filter": "statuscode:200", "collapse": "urlkey", "limit": "20000",
    })
    raw = get("https://web.archive.org/cdx/search/cdx?" + q)
    if not raw:
        sys.exit("Архив не ответил. Попробуйте позже.")
    rows = json.loads(raw)[1:]
    # для каждого адреса берём последний снимок
    q2 = urllib.parse.urlencode({"url": DOMAIN + "/*", "output": "json", "fl": "urlkey,timestamp",
                                 "filter": "statuscode:200", "limit": "50000"})
    latest = {}
    raw2 = get("https://web.archive.org/cdx/search/cdx?" + q2)
    if raw2:
        for k, ts in json.loads(raw2)[1:]:
            if ts > latest.get(k, ""):
                latest[k] = ts
    return rows, latest


class Extract(HTMLParser):
    """Вытаскивает h1, <time datetime>, og:image и HTML внутри первого .entry-content."""
    VOID = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "area", "col", "embed", "param", "track"}
    DROP = {"script", "style", "iframe", "form", "noscript", "svg"}
    CONTENT_RE = re.compile(r"\b(entry-content|post-content|td-post-content|article-content)\b")

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.title = self.h1 = self.date = self.og_image = ""
        self.depth = 0      # глубина внутри .entry-content
        self.skip = 0       # глубина внутри script/style/...
        self.buf = []
        self.done = False
        self.in_title = self.in_h1 = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("property") == "og:image":
            self.og_image = a.get("content") or ""
        if tag == "time" and a.get("datetime") and not self.date:
            self.date = a["datetime"][:10]
        if tag == "title":
            self.in_title = True
        if tag == "h1" and not self.h1:
            self.in_h1 = True
        if not self.depth:
            if not self.done and tag in ("div", "article", "section") and self.CONTENT_RE.search(a.get("class") or ""):
                self.depth = 1
            return
        if tag in self.VOID:
            if not self.skip:
                self.buf.append(self.get_starttag_text())
            return
        self.depth += 1
        if self.skip or tag in self.DROP:
            self.skip += 1
        else:
            self.buf.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if self.depth and not self.skip:
            self.buf.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "h1":
            self.in_h1 = False
        if not self.depth or tag in self.VOID:
            return
        self.depth -= 1
        if self.depth == 0:
            self.done = True
        elif self.skip:
            self.skip -= 1
        else:
            self.buf.append(f"</{tag}>")

    def handle_data(self, d):
        if self.in_title:
            self.title += d
        if self.in_h1:
            self.h1 += d
        if self.depth and not self.skip:
            self.buf.append(d)

    def handle_entityref(self, n):
        self.handle_data(f"&{n};")

    def handle_charref(self, n):
        self.handle_data(f"&#{n};")


def clean_text(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()


def strip_wayback(u):
    m = re.match(r"^(?:https?:)?//web\.archive\.org/web/\d+[a-z_]*/(.+)$", u)
    return m.group(1) if m else u


def save_image(src, ts):
    src = strip_wayback(html.unescape(src))
    if src.startswith("//"): src = "https:" + src
    if src.startswith("/"): src = f"https://{DOMAIN}{src}"
    if DOMAIN not in urllib.parse.urlparse(src).netloc:
        return None
    path = urllib.parse.urlparse(src).path
    ext = os.path.splitext(path)[1].lower()[:5] or ".jpg"
    name = os.path.basename(path)[:60] or hashlib.md5(src.encode()).hexdigest()[:10] + ext
    rel = f"assets/uploads/{name}"
    dst = os.path.join(ROOT, rel)
    if not os.path.exists(dst):
        data = get(f"https://web.archive.org/web/{ts}im_/{src}", binary=True)
        if not data:
            return None
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(data)
    return rel


def sanitize(content, ts):
    content = re.sub(r"(?is)<!--.*?-->", "", content)
    content = re.sub(r'\s(on\w+|style|class|id|srcset|sizes|data-[\w-]+)="[^"]*"', "", content)
    first_img = ""

    def img(m):
        nonlocal first_img
        rel = save_image(m.group(1), ts)
        if not rel:
            return ""
        first_img = first_img or rel
        return f'<img src="{rel}" alt="" loading="lazy">'
    content = re.sub(r'(?is)<img[^>]*?\ssrc="([^"]+)"[^>]*>', img, content)

    def link(m):
        u = strip_wayback(html.unescape(m.group(1)))
        p = urllib.parse.urlparse(u)
        if DOMAIN in p.netloc or (not p.netloc and u.startswith("/")):
            pm = POST_RE.match(p.path)
            if pm: return f'href="#/news/{pm.group(4)}"'
            if re.search(r"\.(pdf|docx?|xlsx?|jpe?g|png)$", p.path, re.I):
                rel = save_image(u, ts)  # тот же загрузчик подходит и для документов
                return f'href="{rel}"' if rel else 'href="#"'
            return f'href="#/news/{p.path.strip("/").split("/")[-1]}"' if p.path.strip("/") else 'href="#/"'
        return f'href="{html.escape(u)}" target="_blank" rel="noopener"'
    content = re.sub(r'href="([^"]+)"', link, content)
    content = re.sub(r"(?s)<(p|div|span)>\s*(&nbsp;)?\s*</\1>", "", content)
    return content.strip(), first_img


def load_json(name, default):
    p = os.path.join(ROOT, "data", name)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()

    news = load_json("news.json", [])
    pages = load_json("pages.json", [])
    by_slug = {n["slug"]: n for n in news}
    pages_by_slug = {p["slug"]: p for p in pages}

    print("Получаю список страниц из архива…")
    rows, latest = cdx()
    todo = []
    for ts, orig, mime, code in rows:
        if "html" not in mime:
            continue
        path = urllib.parse.urlparse(orig).path or "/"
        if SKIP_RE.search(orig) or path == "/":
            continue
        todo.append((ts, orig, path))
    print(f"Найдено HTML-страниц: {len(todo)}")

    done = 0
    for ts, orig, path in todo:
        m = POST_RE.match(path)
        slug = urllib.parse.unquote(m.group(4) if m else path.strip("/").split("/")[-1])
        if not slug:
            continue
        existing = by_slug.get(slug) or pages_by_slug.get(slug)
        if existing and existing.get("restored"):
            continue
        snap_ts = ts
        for k, t in latest.items():
            if k.endswith(path.rstrip("/").lower()) or k.endswith(path.lower()):
                snap_ts = max(snap_ts, t)
                break
        print(f"→ {path}")
        raw = get(f"https://web.archive.org/web/{snap_ts}id_/{orig}")
        time.sleep(args.delay)
        if not raw:
            continue
        ex = Extract()
        try:
            ex.feed(raw)
        except Exception as e:
            print(f"  ! ошибка разбора: {e}")
            continue
        body = "".join(ex.buf)
        if not clean_text(re.sub(r"<[^>]+>", " ", body)):
            print("  (пусто — пропускаю)")
            continue
        content, first_img = sanitize(body, snap_ts)
        title = clean_text(ex.h1) or clean_text(ex.title).split(" | ")[0].split(" – ")[0]
        text = clean_text(re.sub(r"<[^>]+>", " ", content))
        excerpt = (text[:220].rsplit(" ", 1)[0] + "…") if len(text) > 220 else text
        date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ex.date
        image = first_img or (save_image(ex.og_image, snap_ts) if ex.og_image else "") or ""
        item = {"slug": slug, "title": title, "date": date, "original": orig, "image": image,
                "excerpt": excerpt, "content": content, "restored": True}
        if m or (existing in news):
            if existing:
                existing.update(item)
            else:
                news.append(item); by_slug[slug] = item
        else:
            if existing:
                existing.update(item)
            else:
                pages.append(item); pages_by_slug[slug] = item
        done += 1
        if done % 10 == 0:
            write(news, pages)
        if args.limit and done >= args.limit:
            break

    write(news, pages)
    print(f"Готово. Восстановлено: {done}. Проверьте data/news.json и data/pages.json, затем сделайте commit и push.")


def write(news, pages):
    news.sort(key=lambda n: n.get("date") or "", reverse=True)
    for name, data in (("news.json", news), ("pages.json", pages)):
        with open(os.path.join(ROOT, "data", name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
