#!/usr/bin/env python3
"""
Сборка статической копии helpautism.ru из скачанного веб-архива.

  python3 tools/build_site.py            # -> site/

Источники:
  archive/2020/   — полный снимок сайта на 20.10.2020 (дизайн, ресурсы, страницы)
  archive/latest/ — последние версии страниц (новые записи 2021–2026)

Каждая страница сохраняется по тому же адресу, что и на старом сайте
(/2020/10/21/slug/ -> site/2020/10/21/slug/index.html), все ссылки делаются
относительными, поэтому сайт работает и на GitHub Pages, и на любом хостинге.
"""
import html, json, os, re, shutil, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A2020 = os.path.join(ROOT, "archive", "2020")
ALATEST = os.path.join(ROOT, "archive", "latest")
OUT = os.path.join(ROOT, "site")
DOMAIN_RE = r"(?:https?:)?//(?:www\.)?helpautism\.ru"
CONTACT_EMAIL = "helpautismvrn@gmail.com"

# скрипты, которые без WordPress-сервера не работают или не нужны
DROP_SCRIPTS = re.compile(r"woocommerce|wp-embed|comment-reply|admin-ajax|wp-emoji|google-analytics|googletagmanager|mc\.yandex|metrika|contact-form-7|my-calendar|eventON|wpcf7|jquery\.blockUI|js\.cookie|cart-fragments|add-to-cart", re.I)


def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def html_pages(base):
    res = {}
    if not os.path.isdir(base):
        return res
    for d, _, files in os.walk(base):
        for f in files:
            if not f.endswith(".html") or "__" in f:
                continue  # index__hash.html — страницы с ?p=… — дубли
            rel = os.path.relpath(os.path.join(d, f), base).replace(os.sep, "/")
            if rel.startswith(("_ext/", "wp-")) or "/feed/" in rel:
                continue
            with open(os.path.join(d, f), "rb") as fh:
                if b"beget=begetok" in fh.read(3000):
                    continue  # заглушка антибота Beget, а не страница
            res[rel] = os.path.join(d, f)
    return res


def relurl(from_rel, target_path):
    """target_path — путь от корня сайта ('/wp-content/x.css', '/kontakty/')."""
    from_dir = os.path.dirname(from_rel)
    path, _, frag = target_path.partition("#")
    path, _, query = path.partition("?")
    trailing = path.endswith("/")
    tgt = path.strip("/")
    r = os.path.relpath(tgt or ".", from_dir or ".").replace(os.sep, "/")
    if trailing or not tgt:
        r = (r + "/") if r != "." else "./"
    elif r == ".":
        r = "./"
    # ver=… отбрасываем (файлы сохранены без него), прочие параметры оставляем
    query = "&".join(x for x in query.split("&") if x and not x.startswith("ver="))
    if query and not re.search(r"\.(css|js|png|jpe?g|gif|svg|woff2?|ttf|eot)$", path, re.I):
        # ?p=123, ?cat=… — на статике не работают, ведём на главную
        if path in ("", "/"):
            return relurl(from_rel, "/")
    return r + ("#" + frag if frag else "")


def localize(text, from_rel):
    def sub(m):
        return relurl(from_rel, m.group(1) or "/")
    # абсолютные адреса сайта -> относительные
    text = re.sub(DOMAIN_RE + r"(/[^\s\"'<>)]*)?", sub, text)
    return text


def clean_html(text, rel):
    # убрать скрипты, которым нужен сервер WordPress
    def scr(m):
        tag = m.group(0)
        open_tag = tag[:tag.find(">") + 1]
        if "src=" in open_tag:
            return "" if DROP_SCRIPTS.search(open_tag) else tag
        # встроенные скрипты: убираем только счётчики и эмодзи WordPress
        return "" if re.search(r"mc\.yandex|metrika|google-analytics|gtag\(|_wpemojiSettings", tag) else tag
    text = re.sub(r"(?is)<script\b[^>]*>.*?</script>", scr, text)
    text = re.sub(r"(?is)<link[^>]+(?:wlwmanifest|EditURI|pingback|shortlink|alternate[^>]+(?:rss|json|oembed))[^>]*>", "", text)
    text = re.sub(r"(?is)<link[^>]+rel=['\"]https://api\.w\.org/['\"][^>]*>", "", text)
    text = re.sub(r"(?is)<link[^>]+(?:woocommerce|my-calendar|eventon|evcal)[^>]*>", "", text)
    # формы Contact Form 7 -> письмо
    text = re.sub(r'(?is)<form([^>]*?)action="[^"]*"([^>]*class="[^"]*wpcf7-form)',
                  rf'<form\1action="mailto:{CONTACT_EMAIL}" enctype="text/plain"\2', text)
    # поиск по сайту -> Яндекс
    text = re.sub(r'(?is)<form([^>]*?)role="search"([^>]*?)action="[^"]*"',
                  r'<form\1role="search"\2action="https://yandex.ru/search/" target="_blank"', text)
    text = re.sub(r'(?is)(<input[^>]+name=["\']s["\'][^>]*>)', r'\1<input type="hidden" name="site" value="helpautism.ru">', text)
    text = text.replace('name="s"', 'name="text"').replace("name='s'", "name='text'")
    return text


def inject_enhance(text, rel):
    css = relurl(rel, "/assets/enhance.css")
    js = relurl(rel, "/assets/enhance.js")
    text = text.replace("</head>", f'<link rel="stylesheet" href="{css}">\n</head>', 1)
    text = re.sub(r"</body>", f'<script src="{js}" defer></script>\n</body>', text, count=1, flags=re.I)
    return text


def extract_article(text):
    """Заголовок, дата и тело записи из страницы любой темы."""
    t = re.search(r'(?is)<h1[^>]*class="[^"]*entry-title[^"]*"[^>]*>(.*?)</h1>', text) or re.search(r"(?is)<h1[^>]*>(.*?)</h1>", text)
    title = re.sub(r"<[^>]+>", "", t.group(1)).strip() if t else ""
    d = re.search(r'datetime="([^"]+)"', text)
    date = d.group(1)[:10] if d else ""
    m = re.search(r'(?is)<div[^>]+class="[^"]*\bentry-content\b[^"]*"[^>]*>', text)
    body = ""
    if m:
        i, depth = m.end(), 1
        for t2 in re.finditer(r"(?is)<(/?)div\b[^>]*>", text[i:]):
            depth += -1 if t2.group(1) else 1
            if depth == 0:
                body = text[i:i + t2.start()]
                break
    return title, date, body


def main():
    p2020 = html_pages(A2020)
    plat = html_pages(ALATEST)
    if "index.html" not in p2020:
        sys.exit("Нет archive/2020/index.html — сначала скачайте архив")
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)

    # 1. ресурсы (css/js/картинки/шрифты/документы) — копия с исправленными url()
    copied = 0
    for d, _, files in os.walk(A2020):
        for f in files:
            src = os.path.join(d, f)
            rel = os.path.relpath(src, A2020).replace(os.sep, "/")
            if f.endswith(".html") or f.startswith("manifest") or rel.startswith("_ext/"):
                continue
            dst = os.path.join(OUT, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if f.endswith(".css"):
                write(dst, localize(read(src), rel))
            elif f.endswith(".js"):
                # селекторы a[href*=#] ломаются в jQuery без migrate (WP 5.5+)
                js = read(src)
                js = re.sub(r"\[href(\*?)=#\]", r'[href\1="#"]', js)
                write(dst, js)
            else:
                shutil.copy2(src, dst)
            copied += 1

    # шаблон записи (страница записи 2020 года) для новых записей
    tpl_rel = next((r for r in sorted(p2020, reverse=True) if re.match(r"20\d\d/\d\d/\d\d/", r)), None)
    tpl = read(p2020[tpl_rel]) if tpl_rel else None

    pages = dict(p2020)
    made_from_tpl = []
    for rel, path in plat.items():
        if rel in pages:
            continue
        txt = read(path)
        if "zerif-lite" in txt:
            pages[rel] = path
        elif tpl and re.match(r"20\d\d/\d\d/\d\d/", rel):
            title, date, body = extract_article(txt)
            if not body:
                continue
            t_title, _, t_body = extract_article(tpl)
            new = tpl.replace(t_body, body, 1) if t_body else tpl
            if t_title:
                new = re.sub(r'(?is)(<h1[^>]*entry-title[^>]*>).*?(</h1>)', lambda m: m.group(1) + title + m.group(2), new, count=1)
                new = re.sub(r"(?is)<title>.*?</title>", f"<title>{title} | Искра надежды</title>", new, count=1)
            new = re.sub(r'(?is)(<time class="entry-date published" datetime=")[^"]*(">)[^<]*', lambda m: m.group(1) + date + m.group(2) + ".".join(reversed(date.split("-"))), new, count=1)
            pages[rel] = None
            made_from_tpl.append((rel, new))

    news = []
    for rel, path in sorted(pages.items()):
        txt = read(path) if path else dict(made_from_tpl)[rel]
        txt = clean_html(txt, rel)
        txt = localize(txt, rel)
        txt = inject_enhance(txt, rel)
        write(os.path.join(OUT, rel), txt)
        m = re.match(r"(\d{4})/(\d\d)/(\d\d)/([^/]+)/index\.html$", rel)
        if m:
            title, _, _ = extract_article(txt)
            news.append({"date": "-".join(m.groups()[:3]), "slug": m.group(4), "title": html.unescape(title), "url": rel.rsplit("index.html", 1)[0]})

    # 2. своё: анимации, 404, служебное
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    for f in ("enhance.css", "enhance.js"):
        shutil.copy2(os.path.join(ROOT, "assets", f), os.path.join(OUT, "assets", f))
    if os.path.exists(os.path.join(ROOT, "CNAME")):
        shutil.copy2(os.path.join(ROOT, "CNAME"), OUT)
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    news.sort(key=lambda n: n["date"], reverse=True)
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    json.dump(news, open(os.path.join(OUT, "data", "news.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write(os.path.join(OUT, "404.html"), read(os.path.join(ROOT, "tools", "404.html")))

    # 3. отчёт о недостающих ресурсах
    missing = set()
    for d, _, files in os.walk(OUT):
        for f in files:
            if not f.endswith((".html", ".css")):
                continue
            p = os.path.join(d, f)
            for u in re.findall(r'(?:src|href)=["\']([^"\'#?]+)|url\(["\']?([^"\')?#]+)', read(p)):
                u = u[0] or u[1]
                if re.match(r"^(https?:|//|data:|mailto:|tel:|javascript:)", u) or not u.strip():
                    continue
                t = os.path.normpath(os.path.join(d, urllib.parse.unquote(u)))
                if u.endswith("/"):
                    t = os.path.join(t, "index.html")
                if not os.path.exists(t):
                    missing.add(os.path.relpath(t, OUT))
    write(os.path.join(ROOT, "archive", "missing.txt"), "\n".join(sorted(missing)) + "\n")
    print(f"Страниц: {len(pages)} (новых по шаблону: {len(made_from_tpl)}), файлов: {copied}, записей: {len(news)}, не хватает: {len(missing)} (archive/missing.txt)")


if __name__ == "__main__":
    main()
