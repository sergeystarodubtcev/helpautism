#!/usr/bin/env python3
"""
Сборка сайта helpautism.ru: контент — content/*.json (импорт из WordPress), оформление — веб-архив.

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
CONTACT_EMAIL = "helpautismvrn@yandex.ru"
SETTINGS = {}  # content/settings.json — меняется в админке (Настройки)

SOCIAL_ICONS = {
    "vk": ("ВКонтакте", '<path d="M3 7.5h3.6c.2 4 2 5.8 3.4 6.1V7.5h3.3v3.4c1.4-.1 2.9-1.8 3.4-3.4h3.3c-.5 2.5-2.4 4.2-3.7 5 1.3.6 3.4 2.2 4.2 5h-3.6c-.7-1.9-2.2-3.3-4.1-3.5v3.5h-.4C6.3 17.5 3.2 13.6 3 7.5z"/>'),
    "max": ("MAX", '<path d="M12 2.5a9.5 9.5 0 0 0-8.3 14.1L2.5 21.5l5-1.2A9.5 9.5 0 1 0 12 2.5zm4.6 13.2h-2.1v-4.6l-2.5 3.1-2.5-3.1v4.6H7.4V8.3h2l2.6 3.3 2.6-3.3h2z"/>'),
    "ok": ("Одноклассники", '<path d="M12 12.3a4.2 4.2 0 1 0 0-8.4 4.2 4.2 0 0 0 0 8.4zm0-6a1.8 1.8 0 1 1 0 3.6 1.8 1.8 0 0 1 0-3.6zm4.3 7.6a1.2 1.2 0 0 0-1.7-.2 4.6 4.6 0 0 1-5.2 0 1.2 1.2 0 1 0-1.5 1.9c.9.7 2 1.1 3.1 1.3l-2.9 2.9a1.2 1.2 0 1 0 1.7 1.7l2.2-2.2 2.2 2.2a1.2 1.2 0 1 0 1.7-1.7l-2.9-2.9c1.1-.2 2.2-.6 3.1-1.3.5-.4.6-1.2.2-1.7z"/>'),
    "dzen": ("Дзен", '<path d="M12 2c.2 5.6 4.4 9.8 10 10-5.6.2-9.8 4.4-10 10-.2-5.6-4.4-9.8-10-10 5.6-.2 9.8-4.4 10-10z"/>'),
    "telegram": ("Telegram", '<path d="M20.7 4.3 2.9 11.2c-1.2.5-1.2 1.2-.2 1.5l4.6 1.4 1.8 5.4c.2.6.4.8.8.8.4 0 .6-.2.9-.5l2.2-2.1 4.6 3.4c.8.5 1.4.2 1.6-.8l3-14.1c.3-1.3-.5-1.8-1.5-1.4zM8.6 13.6l9.1-5.7c.4-.3.8-.1.5.2l-7.6 6.9-.3 3.2-1.7-4.6z"/>'),
    "youtube": ("YouTube", '<path d="M21.6 7.2a2.6 2.6 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.6 2.6 0 0 0 2.4 7.2 27 27 0 0 0 2 12c0 1.6.1 3.2.4 4.8a2.6 2.6 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.6 2.6 0 0 0 1.8-1.8c.3-1.6.4-3.2.4-4.8s-.1-3.2-.4-4.8zM10 15V9l5.2 3L10 15z"/>'),
}
SOCIAL_PLACEHOLDER = {"max"}  # без ссылки — бледная заглушка; остальные без ссылки скрываются


def social_items():
    """[(ключ, название, ссылка или '', svg)] — пустая ссылка = заглушка «скоро»."""
    soc = SETTINGS.get("social", {})
    return [(k, t, (soc.get(k) or "").strip(), svg) for k, (t, svg) in SOCIAL_ICONS.items()]


def social_icons_html(cls="ha-soc"):
    out = []
    for k, t, url, svg in social_items():
        icon = f'<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">{svg}</svg>'
        if url:
            out.append(f'<a class="{cls} {cls}--{k}" href="{esc(url)}" target="_blank" rel="noopener" title="{t}" aria-label="{t}">{icon}</a>')
        elif k in SOCIAL_PLACEHOLDER:
            out.append(f'<span class="{cls} {cls}--{k} is-soon" title="{t}: ссылка скоро появится" aria-label="{t} (скоро)">{icon}</span>')
    return "".join(out)


def theme_style():
    c = SETTINGS.get("colors", {})
    ok = lambda v: bool(re.match(r"^#[0-9a-fA-F]{6}$", str(v or "")))
    vars_ = "".join(f"--{k}:{c[k]};" for k in ("ink", "accent", "cta") if ok(c.get(k)))
    return f'<style id="ha-theme">:root{{{vars_}}}</style>' if vars_ else ""

HOME_FACTS = {}

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
    # шрифты Google -> локальные (assets/fonts), без обращений к зарубежным серверам
    fonts = relurl(rel, "/assets/fonts/fonts.css")
    text = re.sub(r"(?is)<link[^>]+fonts\.googleapis\.com[^>]*>", "", text)
    text = text.replace("</head>", f'<link rel="stylesheet" href="{fonts}">\n</head>', 1)
    text = re.sub(r"(?:https?:)?//ajax\.googleapis\.com/ajax/libs/jquery/3\.1\.0/jquery\.min\.js", relurl(rel, "/assets/vendor/jquery-3.1.0.min.js"), text)
    css = relurl(rel, "/assets/enhance.css")
    modern = relurl(rel, "/assets/modern.css")
    js = relurl(rel, "/assets/enhance.js")
    cfg = relurl(rel, "/assets/config.js")
    text = text.replace("</head>", f'<link rel="stylesheet" href="{css}">\n<link rel="stylesheet" href="{modern}">\n'
                                   '<meta name="theme-color" content="#1f7fd1">\n</head>', 1)
    text = re.sub(r"</body>", f'<script src="{cfg}"></script>\n<script src="{js}" defer></script>\n</body>', text, count=1, flags=re.I)
    return text


THUMB_RE = re.compile(r"""(\b(?:src|data-src|href)=["'])([^"'#?]+\.(?:jpe?g|png|gif|webp))(["'])""", re.I)


def fix_thumbs(text, rel):
    """Нет уменьшенной копии (img-285x214.jpg) — подставляем оригинал (img.jpg), если он есть."""
    base_dir = os.path.dirname(os.path.join(OUT, rel))

    def fix(m):
        url = m.group(2)
        if re.match(r"^(https?:|//|data:)", url):
            return m.group(0)
        if os.path.exists(os.path.normpath(os.path.join(base_dir, urllib.parse.unquote(url)))):
            return m.group(0)
        orig = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", url)
        if orig != url and os.path.exists(os.path.normpath(os.path.join(base_dir, urllib.parse.unquote(orig)))):
            return m.group(1) + orig + m.group(3)
        return m.group(0)
    text = THUMB_RE.sub(fix, text)
    return re.sub(r"""\s+srcset=["'][^"']*["']""", "", text)  # srcset ссылается на отсутствующие размеры


MS_BLOCK_RE = re.compile(r"(?is)<!--\s*MasterSlider\s*-->.*?<!--\s*END MasterSlider\s*-->")


def _exists(base_dir, url):
    return os.path.exists(os.path.normpath(os.path.join(base_dir, urllib.parse.unquote(url))))


def modernize(text, rel):
    """Чистка тяжёлых/сломанных частей WordPress и подготовка к новому оформлению."""
    base_dir = os.path.dirname(os.path.join(OUT, rel))
    # 1. прелоадер с крутящимся кругом
    text = re.sub(r'(?is)<div class="preloader">\s*<div class="status">.*?</div>\s*</div>', "", text)
    # 2. анимация темы, прятавшая блоки (scrollReveal) — заменена своей
    text = re.sub(r"(?is)<script[^>]+scrollReveal\.js[^>]*>\s*</script>", "", text)
    text = re.sub(r'\sdata-scrollreveal="[^"]*"', "", text)
    # 3. виджет UpToLike (на телефоне растягивался на весь экран) — свои кнопки «Поделиться» в enhance.js
    text = re.sub(r"(?is)<script[^>]*>\s*\(function\(w,doc\)\s*\{\s*if \(!w\.__utlWdgt.*?</script>", "", text)
    text = re.sub(r'(?is)<div[^>]*class="[^"]*uptolike-buttons[^"]*"[^>]*>\s*</div>', "", text)
    # 4. всплывающее окно EventON (кнопка «X» внизу страницы)
    text = re.sub(r'(?is)<div class=[\'"]evo_lightbox.*?</div>\s*</div>\s*</div>\s*</div>', "", text)

    # 5. слайдеры MasterSlider -> сетка фото / карточка с текстом
    def ms(m):
        block = m.group(0)
        imgs = []
        for src in re.findall(r'data-src="([^"]+)"', block):
            for cand in (src, re.sub(r"-scaled(\.\w+)$", r"\1", src), re.sub(r"-\d+x\d+(\.\w+)$", r"\1", src)):
                if _exists(base_dir, cand):
                    imgs.append(cand)
                    break
        infos = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r'(?is)<div class="ms-info">(.*?)</div>', block)]
        out = ""
        if imgs:
            out += '<div class="ha-gallery">' + "".join(f'<a href="{u}" class="ha-gallery__item"><img src="{u}" alt="" loading="lazy"></a>' for u in imgs) + "</div>"
        infos = [x for x in infos if x]
        if infos:
            out += "".join(f'<div class="ha-notice"><p>{x}</p></div>' for x in infos)
        return out
    text = MS_BLOCK_RE.sub(ms, text)
    text = re.sub(r"(?is)<script>\s*\(function\s*\(\s*\$\s*\)\s*\{[^<]*?new MasterSlider\(\).*?</script>", "", text)
    text = re.sub(r"(?is)<script[^>]+master-slider[^>]*>\s*</script>", "", text)
    text = re.sub(r"(?is)<link[^>]+(?:master-slider|msl-)[^>]*>", "", text)

    # 6. главная: первый экран
    if rel == "index.html":
        img = relurl(rel, mapu(SETTINGS.get("hero_image") or "/wp-content/uploads/2020/03/3248611.jpg"))
        hero = ('<div class="ha-hero">'
                '<span class="ha-hero__eyebrow">ВРООИ · Воронеж</span>'
                '<h1 class="ha-hero__title"><span>Искра</span> <span>Надежды</span></h1>'
                '<p class="ha-hero__lead">Помогаем детям и взрослым с аутизмом и их семьям: занятия, поддержка родителей, '
                'правовая помощь, инклюзивные проекты.</p></div>')
        media = f'<figure class="ha-hero__media"><img src="{img}" alt="Детские руки складывают пазл" fetchpriority="high"></figure>'
        facts = ('<div class="ha-hero__facts"><div><b>2008</b><span>год основания</span></div>'
                 f'<div><b>{HOME_FACTS.get("posts", 600)}+</b><span>новостей и статей</span></div>'
                 '<div><b>4</b><span>площадки в Воронеже</span></div></div>')
        text = re.sub(r'(<div class="header-content-wrap"><div class="container">)', lambda m: m.group(1) + hero + media, text, count=1)
        buttons = (f'<div class="buttons"><a href="{esc(pay_url())}" class="btn ha-btn--cta" target="_blank" rel="noopener">Помочь</a>'
                   f'<a href="{relurl(rel, "/zapis/")}" class="btn ha-btn--ghost">Записаться на занятия</a></div>')
        text = re.sub(r'(?s)<div class="buttons">.*?</div>', lambda m: buttons + facts, text, count=1)
        text = text.replace('<body class="home', '<body class="ha-home home', 1)
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


# =====================================================================
#  Сборка из контента (content/*.json, импорт из WordPress)
# =====================================================================
CONTENT = os.path.join(ROOT, "content")
MEDIA = os.path.join(ROOT, "media")
SITE_URL = "https://helpautism.ru"
PER_PAGE = 12
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def ru_date(d):
    try:
        y, m, dd = d.split("-")
        return f"{int(dd)} {MONTHS[int(m) - 1]} {y}"
    except Exception:
        return d


def esc(s):
    return html.escape(s or "", quote=True)


def absu(path):
    """Путь от корня -> абсолютный адрес сайта (его потом делает относительным localize)."""
    return SITE_URL + path if path.startswith("/") else path


def load_content():
    posts, pages = [], []
    for d, _, files in os.walk(os.path.join(CONTENT, "posts")):
        for f in files:
            if f.endswith(".json"):
                doc = json.load(open(os.path.join(d, f), encoding="utf-8"))
                doc["_file"] = os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, "/")
                posts.append(doc)
    for f in os.listdir(os.path.join(CONTENT, "pages")):
        if f.endswith(".json"):
            doc = json.load(open(os.path.join(CONTENT, "pages", f), encoding="utf-8"))
            doc["_file"] = "content/pages/" + f
            pages.append(doc)
    posts.sort(key=lambda p: (p["date"], p["id"]), reverse=True)
    site = json.load(open(os.path.join(CONTENT, "site.json"), encoding="utf-8"))
    forms = json.load(open(os.path.join(CONTENT, "forms.json"), encoding="utf-8"))
    return site, posts, pages, forms


def split_template(tpl):
    """Шапка (до #content) и подвал (с <footer id="footer">) из страницы оригинального сайта."""
    i = tpl.find('<div id="content"')
    j = tpl.find('<footer id="footer"')
    return tpl[:i], tpl[j:]


def menu_html(items, depth=0):
    out = []
    for it in items:
        has = bool(it["children"])
        cls = "menu-item" + (" menu-item-has-children" if has else "")
        out.append(f'<li class="{cls}"><a href="{esc(absu(it["url"]))}">{esc(it["title"])}</a>')
        if has:
            out.append('<ul class="sub-menu">' + menu_html(it["children"], depth + 1) + "</ul>")
        out.append("</li>")
    return "".join(out)


def replace_menu(head, site):
    i = head.find('<ul id="menu-verxnee-menyu"')
    if i < 0:
        return head
    depth, k = 0, i
    for m in re.finditer(r"(?i)<(/?)ul\b", head[i:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            k = i + m.end()
            k = head.find(">", k) + 1
            break
    cta = f'<li class="menu-item ha-nav-cta"><a href="{esc(pay_url())}" target="_blank" rel="noopener">Помочь</a></li>'
    new = '<ul id="menu-verxnee-menyu" class="nav navbar-nav navbar-right responsive-nav main-nav-list">' + menu_html(site["menu"]) + cta + "</ul>"
    return head[:i] + new + head[k:]


def set_title_and_body(head, title, body_class, description=""):
    head = re.sub(r"(?is)<title>.*?</title>", f"<title>{esc(title)}</title>", head, count=1)
    head = re.sub(r'(?is)<meta[^>]+name="description"[^>]*>', "", head)
    if description:
        head = head.replace("</head>", f'<meta name="description" content="{esc(description[:200])}">\n<meta property="og:title" content="{esc(title)}">\n</head>', 1)
    head = re.sub(r'(?is)<body\s+class="[^"]*"', f'<body class="{body_class}"', head, count=1)
    head = re.sub(r'(?is)<link[^>]+rel=["\']canonical["\'][^>]*>', "", head)
    return head


def render_form(fid, forms):
    f = forms["forms"].get(str(fid))
    if f and f.get("alias"):
        fid, f = f["alias"], forms["forms"].get(f["alias"])
    if not f:
        return ""
    rows = []
    for i, fld in enumerate(f["fields"]):
        nid = f"f{fid}-{i}"
        req = " required" if fld.get("required") else ""
        star = ' <span class="ha-req">*</span>' if fld.get("required") else ""
        lab = f'<label for="{nid}">{esc(fld["label"])}{star}</label>'
        t = fld["type"]
        if t == "textarea":
            ctl = f'<textarea id="{nid}" name="{esc(fld["name"])}" rows="5"{req}></textarea>'
        elif t == "select":
            ctl = f'<select id="{nid}" name="{esc(fld["name"])}"{req}>' + "".join(f"<option>{esc(o)}</option>" for o in fld["options"]) + "</select>"
        elif t == "programs":
            lab = f'<span class="ha-field__label">{esc(fld["label"])}</span>'
            ctl = "".join(
                f'<div class="ha-progs"><span class="ha-progs__group">{esc(g.get("group", ""))}</span><div class="ha-checks">' + "".join(
                    f'<label class="ha-check"><input type="checkbox" name="{esc(fld["name"])}" value="{esc(g.get("group", "") + ": " + o)}"><span>{esc(o)}</span></label>'
                    for o in g.get("items", [])) + "</div></div>"
                for g in SETTINGS.get("programs", []) if g.get("items"))
        elif t == "checkbox":
            lab = f'<span class="ha-field__label">{esc(fld["label"])}</span>'
            ctl = '<div class="ha-checks">' + "".join(
                f'<label class="ha-check"><input type="checkbox" name="{esc(fld["name"])}" value="{esc(o)}"><span>{esc(o)}</span></label>' for o in fld["options"]) + "</div>"
        else:
            ctl = f'<input id="{nid}" type="{t}" name="{esc(fld["name"])}"{req}>'
        rows.append(f'<div class="ha-field ha-field--{t}">{lab}{ctl}</div>')
    consent = ('<label class="ha-check ha-consent"><input type="checkbox" name="Согласие" value="да" required>'
               '<span>Я даю согласие на обработку персональных данных в соответствии с '
               f'<a href="{absu("/personal-data-usage-terms/")}" target="_blank">условиями</a></span></label>')
    return (f'<form class="ha-form" data-form-id="{fid}" data-form-title="{esc(f["title"])}" data-email="{esc(forms["email"])}" novalidate>'
            f'<h3 class="ha-form__title">{esc(f["title"])}</h3>' + "".join(rows) + consent +
            '<button type="submit" class="ha-btn">Отправить</button><p class="ha-form__status" role="status"></p></form>')


def render_table(tid, site):
    tables = site.get("tables", {})
    keys = sorted(tables, key=lambda k: int(k))
    try:
        rows = tables[keys[int(tid) - 1]]
    except Exception:
        return ""
    if not rows:
        return ""
    head = "".join(f"<th>{c}</th>" for c in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f'<div class="ha-table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


DONATE_HTML = ('<div class="ha-donate"><h3>Поддержать «Искру Надежды»</h3>'
               '<p>Пожертвовать можно онлайн картой или через СБП, а также переводом по реквизитам.</p>'
               '<a class="ha-btn ha-btn--cta" href="%%PAY%%" target="_blank" rel="noopener">Помочь</a></div>')


def pay_url():
    u = (SETTINGS.get("donate", {}) or {}).get("url", "").strip()
    return u if re.match(r"^https://", u) else absu("/kontakty/")


def donate_form_html():
    d = SETTINGS.get("donate", {})
    amounts = [int(a) for a in d.get("amounts", [300, 500, 1000, 3000]) if str(a).isdigit()]
    chips = "".join(f'<label class="ha-amount"><input type="radio" name="amount" value="{a}"{" checked" if i == 1 else ""}><span>{a:,} ₽</span></label>'.replace(",", " ")
                    for i, a in enumerate(amounts))
    return ('<form class="ha-donate-form" novalidate>'
            f'<div class="ha-amounts">{chips}<label class="ha-amount ha-amount--other"><input type="radio" name="amount" value="other"><span>Другая сумма</span></label></div>'
            '<div class="ha-field ha-other hidden"><label for="don-other">Сумма, ₽</label><input id="don-other" type="number" min="10" max="1000000" step="1" inputmode="numeric"></div>'
            '<div class="ha-field"><label for="don-email">E-mail для чека <span class="ha-req">*</span></label><input id="don-email" type="email" required autocomplete="email"></div>'
            '<div class="ha-field"><label for="don-name">Имя (необязательно)</label><input id="don-name" type="text" autocomplete="name"></div>'
            '<label class="ha-check ha-consent"><input type="checkbox" required><span>Я принимаю '
            f'<a href="{absu("/donation-service-terms/")}" target="_blank">условия пожертвования</a> и даю согласие на обработку персональных данных</span></label>'
            '<button type="submit" class="ha-btn ha-btn--cta">Пожертвовать</button><p class="ha-form__status" role="status"></p></form>')


RENAMES = {}


def mapu(path):
    """Учитывает переименование PNG -> JPEG при сжатии медиа."""
    return RENAMES.get(urllib.parse.unquote(path), path) if path else path


def media_exists(path):
    rel = urllib.parse.unquote(mapu(path)).lstrip("/")
    return os.path.exists(os.path.join(OUT, rel))


def render_body(doc, site, forms):
    c = doc["content"]
    c = re.sub(r'<div class="ha-form" data-form="(\d+)"></div>', lambda m: render_form(m.group(1), forms), c)
    c = re.sub(r'<div class="ha-table" data-table="(\d+)"></div>', lambda m: render_table(m.group(1), site), c)
    c = c.replace('<div class="ha-donate-slot"></div>', DONATE_HTML.replace("%%PAY%%", esc(pay_url())))
    gal = [u for u in doc.get("gallery", []) if media_exists(u)]
    gal_html = ('<div class="ha-gallery">' + "".join(f'<a href="{absu(mapu(u))}" class="ha-gallery__item"><img src="{absu(mapu(u))}" alt="" loading="lazy"></a>' for u in gal) + "</div>") if gal else ""
    if '<div class="ha-gallery-slot"></div>' in c:
        c = c.replace('<div class="ha-gallery-slot"></div>', gal_html, 1).replace('<div class="ha-gallery-slot"></div>', "")
    # ссылки от корня -> абсолютные (localize потом сделает относительными)
    c = re.sub(r'((?:src|href|poster)=["\'])(/[^"\']*)', lambda m: m.group(1) + absu(mapu(m.group(2))), c)
    c = re.sub(r'\s+srcset="[^"]*"', "", c)
    return c


def cat_links(doc, site):
    out = []
    for s in doc.get("categories", []):
        c = site["categories"].get(s)
        if c:
            out.append(f'<a class="ha-tag" href="{absu(c["path"])}">{esc(c["name"])}</a>')
    return "".join(out)


def card(doc, site):
    thumb = doc.get("thumbnail")
    if not thumb or not media_exists(thumb):
        m = re.search(r'src=["\'](/wp-content/uploads/[^"\']+\.(?:jpe?g|png|webp))', doc["content"], re.I)
        thumb = m.group(1) if m and media_exists(m.group(1)) else ""
    img = (f'<img src="{absu(mapu(thumb))}" alt="" loading="lazy">' if thumb else '<span class="ha-card__noimg"></span>')
    cats = [site["categories"][s]["name"] for s in doc.get("categories", []) if s in site["categories"] and s != "news"]
    return (f'<article class="ha-card"><a class="ha-card__media" href="{absu(doc["path"])}" tabindex="-1" aria-hidden="true">{img}</a>'
            f'<div class="ha-card__body"><div class="ha-card__meta"><time datetime="{doc["date"]}">{ru_date(doc["date"])}</time>'
            + (f'<span>{esc(cats[0])}</span>' if cats else "") +
            f'</div><h3 class="ha-card__title"><a href="{absu(doc["path"])}">{esc(doc["title"])}</a></h3>'
            f'<p class="ha-card__text">{esc(doc["excerpt"][:180])}</p></div></article>')


def main_wrap(inner, cls=""):
    return (f'<div id="content" class="site-content"><div class="container ha-container {cls}"><div id="primary" class="content-area">'
            f'<main id="main" class="site-main" role="main">{inner}</main></div></div></div>')


FOOTER = (
    '<footer id="footer" class="ha-footer"><div class="container ha-footer__grid">'
    '<div class="ha-footer__brand"><a href="https://helpautism.ru/" class="ha-footer__logo"><img src="https://helpautism.ru/wp-content/uploads/2017/01/logo-1.png" alt="" width="64" height="64">'
    '<span>ВРООИ<br><b>Искра Надежды</b></span></a>'
    '<p>Воронежская региональная общественная организация инвалидов и родителей детей-инвалидов с нарушениями психического развития аутистического спектра.</p></div>'
    '<div><h4>Контакты</h4><ul class="ha-footer__list">'
    '<li><a href="tel:+79202111202">8 920 211-12-02</a> — администратор</li>'
    '<li><a href="tel:+74732478823">8 473 247-88-23</a> — городской</li>'
    '<li><a href="mailto:helpautismvrn@yandex.ru">helpautismvrn@yandex.ru</a></li>'
    '<li><a href="mailto:iskranadezhdy@helpautism.ru">iskranadezhdy@helpautism.ru</a></li></ul></div>'
    '<div><h4>Где мы занимаемся</h4><ul class="ha-footer__list">'
    '<li>ул. Средне-Московская, 14</li><li>ул. Хользунова, 74 (вход со двора)</li><li>ул. Переверткина, 11 (вход с торца)</li><li>ул. Туполева, 39 (вход с торца)</li></ul></div>'
    '<div><h4>Разделы</h4><ul class="ha-footer__list">'
    '<li><a href="https://helpautism.ru/category/news/">Новости</a></li>'
    '<li><a href="https://helpautism.ru/category/deyatelnost/">Деятельность</a></li>'
    '<li><a href="https://helpautism.ru/my-informiruem/">Информирование</a></li>'
    '<li><a href="https://helpautism.ru/deyatelnost/">О нас</a></li>'
    '<li><a href="https://helpautism.ru/question/">Задать вопрос</a></li></ul>'
    '<div class="ha-footer__social">%%SOCIAL%%</div></div>'
    '</div><div class="container ha-footer__bottom"><span>© 2008–' + __import__("datetime").date.today().strftime("%Y") + ' ВРООИ «Искра Надежды»</span>'
    '<span><a href="https://helpautism.ru/kontakty/">Реквизиты</a> · <a href="https://helpautism.ru/personal-data-usage-terms/">Персональные данные</a> · '
    '<a href="https://helpautism.ru/osnovnye-svedeniya/">Сведения об организации</a></span></div></footer>')


def pipeline(text, rel):
    # новый подвал вместо подвала 2020 года (старые адрес/телефоны, календарь, приватное видео)
    i = text.find('<footer id="footer"')
    j = text.find("</footer>", i)
    if i >= 0 and j > i:
        text = text[:i] + FOOTER.replace("%%SOCIAL%%", social_icons_html("ha-fsoc")) + text[j + len("</footer>"):]
    # верхняя полоса: почта + ВКонтакте, Telegram, Max, Одноклассники, YouTube (без Instagram/Facebook)
    text = re.sub(r'(?is)<div class="social-block">.*?</div>',
                  lambda m: '<div class="social-block"><a href="mailto:helpautismvrn@yandex.ru" class="ha-topmail">helpautismvrn@yandex.ru</a>'
                            + social_icons_html("ha-soc") + "</div>", text, count=1)
    text = text.replace("helpautismvrn@gmail.com", "helpautismvrn@yandex.ru")  # актуальная почта со страницы «Контакты»
    text = clean_html(text, rel)
    text = localize(text, rel)
    text = inject_enhance(text, rel)
    text = fix_thumbs(text, rel)
    text = modernize(text, rel)
    text = text.replace("</head>", theme_style() + "</head>", 1)  # цвета из админки — после остальных стилей
    return text


def page_out(path):
    rel = path.strip("/")
    return (rel + "/index.html") if rel else "index.html"


def main():
    if not os.path.exists(os.path.join(A2020, "index.html")):
        sys.exit("Нет archive/2020/index.html — сначала скачайте архив")
    site, posts, pages, forms = load_content()
    sp = os.path.join(CONTENT, "settings.json")
    SETTINGS.clear()
    SETTINGS.update(json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {})
    rn = os.path.join(MEDIA, "renames.json")
    if os.path.exists(rn):
        RENAMES.update(json.load(open(rn)))
    HOME_FACTS["posts"] = (len(posts) // 10) * 10
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)

    # 1. оформление и файлы старого сайта (тема, плагины, картинки из архива)
    copied = 0
    for d, _, files in os.walk(A2020):
        for f in files:
            src = os.path.join(d, f)
            rel = os.path.relpath(src, A2020).replace(os.sep, "/")
            if f.endswith(".html") or f.startswith("manifest") or rel.startswith("_ext/") or not rel.startswith("wp-"):
                continue
            dst = os.path.join(OUT, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if f.endswith(".css"):
                write(dst, localize(read(src), rel))
            elif f.endswith(".js"):
                write(dst, re.sub(r"\[href(\*?)=#\]", r'[href\1="#"]', read(src)))
            else:
                shutil.copy2(src, dst)
            copied += 1
    # медиафайлы с сайта (импорт WordPress) — поверх архивных
    if os.path.isdir(MEDIA):
        shutil.copytree(MEDIA, OUT, dirs_exist_ok=True, ignore=shutil.ignore_patterns("renames.json", "skipped.txt"))

    tpl = read(os.path.join(A2020, "2020", "10", "05", "voskresnaya-vstrecha", "index.html"))
    head0, foot0 = split_template(tpl)
    head0 = replace_menu(head0, site)
    head0 = re.sub(r'(?is)<div class="preloader">.*?</div>\s*</div>', "", head0)

    def emit(path, title, body_class, inner, description=""):
        rel = page_out(path)
        head = set_title_and_body(head0, title, body_class, description)
        write(os.path.join(OUT, rel), pipeline(head + inner + foot0, rel))
        return rel

    n = 0
    # 2. записи
    for i, p in enumerate(posts):
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None
        thumb = p.get("thumbnail")
        hero = (f'<figure class="ha-post__cover"><img src="{absu(mapu(thumb))}" alt=""></figure>'
                if thumb and media_exists(thumb) and thumb not in p["content"] and not p.get("gallery") else "")
        nav = '<nav class="ha-postnav">'
        if older:
            nav += f'<a class="ha-postnav__prev" href="{absu(older["path"])}"><small>Предыдущая</small><span>{esc(older["title"])}</span></a>'
        if newer:
            nav += f'<a class="ha-postnav__next" href="{absu(newer["path"])}"><small>Следующая</small><span>{esc(newer["title"])}</span></a>'
        nav += "</nav>"
        art = (f'<article class="post type-post hentry ha-post"><header class="entry-header">'
               f'<div class="ha-post__meta"><time datetime="{p["date"]}">{ru_date(p["date"])}</time>{cat_links(p, site)}</div>'
               f'<h1 class="entry-title">{esc(p["title"])}</h1></header>{hero}'
               f'<div class="entry-content">{render_body(p, site, forms)}</div></article>{nav}')
        emit(p["path"], f'{p["title"]} | Искра Надежды', "single single-post", main_wrap(art, "ha-narrow"), p["excerpt"])
        n += 1

    # 3. страницы
    for pg in pages:
        art = (f'<article class="page type-page hentry ha-post"><header class="entry-header"><h1 class="entry-title">{esc(pg["title"])}</h1></header>'
               f'<div class="entry-content">{render_body(pg, site, forms)}</div></article>')
        emit(pg["path"], f'{pg["title"]} | Искра Надежды', "page", main_wrap(art, "ha-narrow"), pg["excerpt"])
        n += 1

    # 3а. свои страницы: пожертвование, спасибо, запись на занятия
    d = SETTINGS.get("donate", {})
    donate = (f'<article class="page hentry ha-post"><header class="entry-header"><h1 class="entry-title">{esc(d.get("title", "Помочь"))}</h1></header>'
              f'<div class="entry-content"><p class="ha-lead">{esc(d.get("text", ""))}</p>'
              f'<div class="ha-donate-box"><a class="ha-btn ha-btn--cta ha-btn--big" href="{esc(pay_url())}" target="_blank" rel="noopener">Пожертвовать онлайн</a>'
              '<p class="ha-hint">Оплата картой на защищённой странице банка-эквайера (Совкомбанк). Платёж поступает на счёт ВРООИ «Искра Надежды».</p></div>'
              '<h2>Другие способы помочь</h2><ul>'
              f'<li>Перевод по реквизитам — <a href="{absu("/kontakty/")}">реквизиты организации</a>, назначение платежа: «Благотворительное пожертвование».</li>'
              f'<li>Стать волонтёром — <a href="{absu("/anketa-volontera/")}">анкета волонтёра</a>.</li>'
              f'<li>Рассказать о нас друзьям — поделитесь ссылкой на сайт.</li></ul></div></article>')
    emit("/pomoch/", "Помочь | Искра Надежды", "page ha-donate-page", main_wrap(donate, "ha-narrow"), d.get("text", ""))
    thanks = ('<article class="page hentry ha-post"><header class="entry-header"><h1 class="entry-title">Спасибо за помощь!</h1></header>'
              '<div class="entry-content"><p>Ваше пожертвование очень важно для детей и взрослых с аутизмом и их семей. '
              'Спасибо, что вы с нами.</p>'
              f'<p><a class="ha-btn" href="{absu("/")}">На главную</a></p></div></article>')
    emit("/spasibo/", "Спасибо | Искра Надежды", "page", main_wrap(thanks, "ha-narrow"))
    zapis = ('<article class="page hentry ha-post"><header class="entry-header"><h1 class="entry-title">Запись на занятия</h1></header>'
             '<div class="entry-content"><p>Заполните форму — мы свяжемся с вами, расскажем о занятиях и пригласим. '
             'Можно записать ребёнка, подростка или взрослого.</p>'
             + render_form("zapis", forms) +
             '<p>Или позвоните: <a href="tel:+79202111202">8 920 211-12-02</a> (администратор).</p></div></article>')
    emit("/zapis/", "Запись на занятия | Искра Надежды", "page", main_wrap(zapis, "ha-narrow"), "Запись на занятия в ВРООИ «Искра Надежды»")
    n += 3

    # 4. рубрики (с подрубриками) с постраничной навигацией
    children = {}
    for s, c in site["categories"].items():
        children.setdefault(c["parent"], []).append(s)
    def descendants(s):
        out = {s}
        for ch in children.get(s, []):
            out |= descendants(ch)
        return out
    for s, c in site["categories"].items():
        group = descendants(s)
        items = [p for p in posts if group & set(p.get("categories", []))]
        if not items:
            continue
        subs = "".join(f'<a class="ha-chip" href="{absu(site["categories"][x]["path"])}">{esc(site["categories"][x]["name"])}</a>'
                       for x in children.get(s, []) if any(x in p.get("categories", []) for p in posts) or children.get(x))
        pages_n = (len(items) + PER_PAGE - 1) // PER_PAGE
        for pn in range(1, pages_n + 1):
            chunk = items[(pn - 1) * PER_PAGE: pn * PER_PAGE]
            pager = ""
            if pages_n > 1:
                links = []
                for k in range(1, pages_n + 1):
                    if k in (1, pages_n) or abs(k - pn) <= 2:
                        href = absu(c["path"] + (f"page/{k}/" if k > 1 else ""))
                        links.append(f'<a class="{"is-current" if k == pn else ""}" href="{href}">{k}</a>')
                    elif links and links[-1] != "<span>…</span>":
                        links.append("<span>…</span>")
                pager = '<nav class="ha-pager">' + "".join(links) + "</nav>"
            inner = (f'<header class="ha-listhead"><span class="ha-eyebrow">Рубрика</span><h1>{esc(c["name"])}</h1>'
                     f'<p>{len(items)} {"запись" if len(items) % 10 == 1 and len(items) % 100 != 11 else "записей"}</p>'
                     + (f'<div class="ha-chips">{subs}</div>' if subs else "") + '</header>'
                     f'<div class="ha-grid">{"".join(card(p, site) for p in chunk)}</div>{pager}')
            path = c["path"] + (f"page/{pn}/" if pn > 1 else "")
            emit(path, f'{c["name"]}' + (f" — страница {pn}" if pn > 1 else "") + " | Искра Надежды", "archive category", main_wrap(inner, "ha-wide"))
            n += 1

    # 5. главная: оригинальная главная + свежие новости
    home = read(os.path.join(A2020, "index.html"))
    home = replace_menu(home, site)
    news = [p for p in posts if "news" in p.get("categories", [])][:6] or posts[:6]
    grid = ('<div class="ha-grid ha-grid--home">' + "".join(card(p, site) for p in news) + "</div>"
            f'<div class="ha-more"><a class="ha-btn ha-btn--ghost" href="{absu("/category/news/")}">Все новости</a></div>')
    i = home.find('<div class="pt-cv-wrapper">')
    if i >= 0:
        depth = 0
        for m in re.finditer(r"(?i)<(/?)div\b[^>]*>", home[i:]):
            depth += -1 if m.group(1) else 1
            if depth == 0:
                home = home[:i] + grid + home[i + m.end():]
                break
    if "ha-grid--home" not in home:
        print("! блок новостей на главной не найден")
    home = re.sub(r'(?is)<div class="preloader">.*?</div>\s*</div>', "", home)
    write(os.path.join(OUT, "index.html"), pipeline(home, "index.html"))
    n += 1

    # переадресация со старых адресов (рубрики без родителя в адресе, старые разделы)
    redirects = {"/category/autism/": "/category/news/", "/category/events/": "/category/news/", "/category/stop-diskriminaciya/": "/category/news/",
                 "/category/news/blog/": "/category/news/", "/category/news/preview/": "/category/news/", "/category/news/press/": "/category/news/smi-o-nas/",
                 "/campaign/na-ustavnuyu-deyatelnost-organizacii/": "/kontakty/", "/blog/": "/category/news/"}
    for s_, c in site["categories"].items():
        flat = f"/category/{s_}/"
        if c["path"] != flat:
            redirects[flat] = c["path"]
    for old, new in redirects.items():
        rel = page_out(old)
        if os.path.exists(os.path.join(OUT, rel)):
            continue
        target = relurl(rel, new)
        write(os.path.join(OUT, rel), f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={target}">'
              f'<link rel="canonical" href="{SITE_URL}{new}"><title>Переход…</title><a href="{target}">Перейти</a>')

    # 6. служебное
    for sub in ("fonts", "vendor"):
        shutil.copytree(os.path.join(ROOT, "assets", sub), os.path.join(OUT, "assets", sub), dirs_exist_ok=True)
    for f in ("enhance.css", "enhance.js", "modern.css", "config.js"):
        if os.path.exists(os.path.join(ROOT, "assets", f)):
            shutil.copy2(os.path.join(ROOT, "assets", f), os.path.join(OUT, "assets", f))
    if os.path.exists(os.path.join(ROOT, "CNAME")):
        shutil.copy2(os.path.join(ROOT, "CNAME"), OUT)
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    json.dump([{"date": p["date"], "title": p["title"], "url": p["path"], "categories": p.get("categories", [])} for p in posts],
              open(os.path.join(OUT, "data", "news.json"), "w", encoding="utf-8"), ensure_ascii=False)
    write(os.path.join(OUT, "404.html"), read(os.path.join(ROOT, "tools", "404.html")))
    urls = ["/"] + [p["path"] for p in posts] + [p["path"] for p in pages] + [c["path"] for c in site["categories"].values()]
    write(os.path.join(OUT, "sitemap.xml"), '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"<url><loc>{SITE_URL}{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n")
    write(os.path.join(OUT, "robots.txt"), f"User-agent: *\nDisallow: /admin/\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")

    # админка: страница + список записей для неё
    shutil.copytree(os.path.join(ROOT, "admin"), os.path.join(OUT, "admin"), dirs_exist_ok=True)
    row = lambda p: {"file": p["_file"], "title": p["title"], "date": p.get("date", ""), "path": p["path"], "categories": p.get("categories", [])}
    json.dump({"posts": [row(p) for p in posts], "pages": [row(p) for p in pages], "categories": site["categories"]},
              open(os.path.join(OUT, "data", "admin.json"), "w", encoding="utf-8"), ensure_ascii=False)
    # адрес облачной функции (подставляется при выкладке в Яндекс Облако)
    api = os.environ.get("HA_API_URL", "").strip()
    if api:
        # на домене helpautism.ru — через api.helpautism.ru (адрес functions.yandexcloud.net режут мобильные операторы)
        write(os.path.join(OUT, "assets", "config.js"),
              "(function () {\n" + ("  if (location.protocol === \"http:\" && /(^|\\.)helpautism\\.ru$/.test(location.hostname)) { location.replace(\"https://\" + location.host + location.pathname + location.search + location.hash); }\n" if os.environ.get("HA_FORCE_HTTPS") == "1" else "") + "  var api = /(^|\\.)helpautism\\.ru$/.test(location.hostname) ? \"https://api.helpautism.ru/\" : " + json.dumps(api) + ";\n"
              "  window.HA_CONFIG = { API_URL: api, FORMS_ENDPOINT: api + \"?a=form\" };\n})();\n")

    # 7. отчёт о недостающих файлах
    missing = set()
    for d, _, files in os.walk(OUT):
        for f in files:
            if not f.endswith(".html"):
                continue
            p = os.path.join(d, f)
            for u in re.findall(r'(?:src|href)=["\']([^"\'#?]+)', read(p)):
                if re.match(r"^(https?:|//|data:|mailto:|tel:|javascript:)", u) or not u.strip():
                    continue
                t = os.path.normpath(os.path.join(d, urllib.parse.unquote(u)))
                if u.endswith("/"):
                    t = os.path.join(t, "index.html")
                if not os.path.exists(t):
                    missing.add(os.path.relpath(t, OUT))
    write(os.path.join(ROOT, "archive", "missing.txt"), "\n".join(sorted(missing)) + "\n")
    print(f"Страниц: {n} (записей {len(posts)}, страниц {len(pages)}), файлов оформления: {copied}, битых ссылок: {len(missing)} (archive/missing.txt)")


if __name__ == "__main__":
    main()
