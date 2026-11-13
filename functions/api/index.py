"""
API сайта «Искра Надежды» (Yandex Cloud Functions, Python 3.12, без зависимостей).

Запросы: POST/GET https://functions.yandexcloud.net/<id>?a=<действие>

  a=login   {password}                    -> {token}
  a=get     ?file=content/posts/2026/x.json -> документ записи        (нужен токен)
  a=save    {doc, file?}                  -> {file, path}            (нужен токен)
  a=delete  {file}                        -> {ok}                    (нужен токен)
  a=upload  {name, data(base64)}          -> {url}                   (нужен токен)
  a=form    {form, title, fields, page}   -> {ok}   письмо с формы сайта на почту

Сохранение = коммит в GitHub; после коммита GitHub Actions пересобирает сайт и выкладывает его.

Переменная окружения HA_SECRETS — base64(JSON) с ключами:
  ADMIN_PASSWORD, GH_TOKEN, GH_REPO ("owner/repo"), GH_BRANCH, SMTP_USER, SMTP_PASSWORD, FORMS_TO
"""
import base64, hashlib, hmac, html, json, os, re, smtplib, ssl, time, urllib.error, urllib.request
from email.message import EmailMessage
from email.utils import formataddr

_cfg = None


def cfg():
    global _cfg
    if _cfg is None:
        raw = os.environ.get("HA_SECRETS", "")
        _cfg = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode()) if raw else {}
        for k in ("ADMIN_PASSWORD", "GH_TOKEN", "GH_REPO", "GH_BRANCH", "SMTP_USER", "SMTP_PASSWORD", "FORMS_TO"):
            _cfg.setdefault(k, os.environ.get(k, ""))
    return _cfg


CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type, X-Admin-Token",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Content-Type": "application/json; charset=utf-8"}


def resp(code, body):
    return {"statusCode": code, "headers": CORS, "body": json.dumps(body, ensure_ascii=False)}


class HttpErr(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


# ---------- авторизация (токен = подпись HMAC, живёт 12 часов) ----------
def _key():
    c = cfg()
    return hashlib.sha256(("ha|" + c["ADMIN_PASSWORD"] + "|" + c["GH_TOKEN"]).encode()).digest()


def make_token():
    exp = str(int(time.time()) + 12 * 3600)
    sig = hmac.new(_key(), exp.encode(), hashlib.sha256).hexdigest()
    return exp + "." + sig


def check_token(event):
    h = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    # свой заголовок: «Authorization» Яндекс Облако принимает за IAM-токен и отклоняет запрос
    tok = (h.get("x-admin-token") or "").strip()
    try:
        exp, sig = tok.split(".", 1)
        good = hmac.new(_key(), exp.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, good) and int(exp) > time.time():
            return
    except Exception:
        pass
    raise HttpErr(401, "Нужно войти заново")


_fails = {}


def login(body, ip):
    c = cfg()
    now = time.time()
    n, t0 = _fails.get(ip, (0, now))
    if n >= 8 and now - t0 < 900:
        raise HttpErr(429, "Слишком много попыток, подождите 15 минут")
    if not c["ADMIN_PASSWORD"] or not hmac.compare_digest(str(body.get("password", "")).encode(), c["ADMIN_PASSWORD"].encode()):
        _fails[ip] = (n + 1, t0 if n else now)
        time.sleep(1)
        raise HttpErr(403, "Неверный пароль")
    _fails.pop(ip, None)
    return {"token": make_token()}


# ---------- GitHub ----------
def gh(method, path, data=None):
    c = cfg()
    req = urllib.request.Request("https://api.github.com/repos/" + c["GH_REPO"] + path, method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Authorization": "Bearer " + c["GH_TOKEN"], "Accept": "application/vnd.github+json",
                                          "User-Agent": "helpautism-admin", "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise HttpErr(502, f"GitHub: {e.code} {e.read()[:200].decode(errors='replace')}")


def gh_file(path):
    return gh("GET", "/contents/" + urllib.request.quote(path) + "?ref=" + urllib.request.quote(cfg()["GH_BRANCH"]))


def gh_put(path, content_bytes, message, sha=None):
    data = {"message": message, "content": base64.b64encode(content_bytes).decode(), "branch": cfg()["GH_BRANCH"],
            "committer": {"name": "Админка сайта", "email": "admin@helpautism.ru"}}
    if sha:
        data["sha"] = sha
    return gh("PUT", "/contents/" + urllib.request.quote(path), data)


def gh_delete(path, message):
    f = gh_file(path)
    if not f:
        return
    gh("DELETE", "/contents/" + urllib.request.quote(path), {"message": message, "sha": f["sha"], "branch": cfg()["GH_BRANCH"],
                                                             "committer": {"name": "Админка сайта", "email": "admin@helpautism.ru"}})


# ---------- записи ----------
FILE_RE = re.compile(r"^content/(posts/\d{4}|pages)/[a-z0-9_\-%.]+\.json$", re.I)
TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "j", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f", "h", "c", "ch", "sh", "shh", "", "y", "", "e", "yu", "ya"]))


def slugify(s):
    s = "".join(TR.get(ch, ch) for ch in (s or "").lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:70].strip("-") or "zapis"


def clean_html(h):
    h = re.sub(r"(?is)<(script|style|iframe(?![^>]*(youtube|vk\.com|vkvideo|rutube))|object|embed)[^>]*>.*?</\1>", "", h or "")
    h = re.sub(r"(?is)\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", h)
    h = re.sub(r"(?is)javascript:", "", h)
    return h.strip()


def excerpt(h, n=220):
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:n].rsplit(" ", 1)[0] + "…") if len(t) > n else t


def get_doc(q):
    f = q.get("file", "")
    if not FILE_RE.match(f):
        raise HttpErr(400, "Неверный файл")
    r = gh_file(f)
    if not r:
        raise HttpErr(404, "Запись не найдена")
    return {"file": f, "doc": json.loads(base64.b64decode(r["content"]).decode())}


def save_doc(body):
    d = body.get("doc") or {}
    title = str(d.get("title", "")).strip()
    if not title:
        raise HttpErr(400, "Нужен заголовок")
    typ = "page" if d.get("type") == "page" else "post"
    date = str(d.get("date") or time.strftime("%Y-%m-%d"))
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HttpErr(400, "Неверная дата")
    slug = slugify(d.get("slug") or title)
    content = clean_html(d.get("content", ""))
    old = body.get("file") or ""
    if old and not FILE_RE.match(old):
        raise HttpErr(400, "Неверный файл")
    prev = {}
    if old:
        r = gh_file(old)
        if r:
            prev = json.loads(base64.b64decode(r["content"]).decode())
    doc = dict(prev)
    doc.update({
        "id": prev.get("id") or int(time.time()), "type": typ, "slug": slug, "title": title, "date": date,
        "modified": time.strftime("%Y-%m-%d"),
        "categories": [re.sub(r"[^a-z0-9_-]", "", c) for c in d.get("categories", []) if c][:10],
        "thumbnail": str(d.get("thumbnail") or ""), "gallery": [str(x) for x in d.get("gallery", [])][:200],
        "excerpt": str(d.get("excerpt") or "").strip() or excerpt(content), "content": content,
    })
    if typ == "post":
        doc["path"] = f"/{date[:4]}/{date[5:7]}/{date[8:10]}/{slug}/"
        new = f"content/posts/{date[:4]}/{slug}.json"
    else:
        doc["path"] = prev.get("path") or f"/{slug}/"
        new = old or f"content/pages/{slug}.json"
    data = json.dumps(doc, ensure_ascii=False, indent=1).encode()
    existing = gh_file(new)
    if existing and new != old:
        raise HttpErr(409, "Запись с таким адресом уже есть — измените заголовок или адрес")
    gh_put(new, data, f"Админка: {title[:60]}", existing["sha"] if existing else None)
    if old and old != new:
        gh_delete(old, f"Админка: перенос «{title[:50]}»")
    return {"file": new, "path": doc["path"]}


def delete_doc(body):
    f = body.get("file", "")
    if not FILE_RE.match(f):
        raise HttpErr(400, "Неверный файл")
    gh_delete(f, "Админка: удалена запись " + f.rsplit("/", 1)[-1])
    return {"ok": True}


def upload(body):
    name = str(body.get("name", "image.jpg"))
    ext = (name.rsplit(".", 1)[-1] if "." in name else "jpg").lower()
    if ext not in ("jpg", "jpeg", "png", "webp", "gif", "pdf", "docx", "doc", "xlsx", "pptx"):
        raise HttpErr(400, "Такой тип файла нельзя загрузить")
    raw = base64.b64decode(body.get("data", ""))
    if len(raw) > 15 * 1024 * 1024:
        raise HttpErr(413, "Файл больше 15 МБ")
    base = slugify(name.rsplit(".", 1)[0])
    ym = time.strftime("%Y/%m")
    rel = f"wp-content/uploads/{ym}/{base}-{int(time.time()) % 100000}.{ext}"
    gh_put("media/" + rel, raw, "Админка: файл " + rel.rsplit("/", 1)[-1])
    return {"url": "/" + rel}


# ---------- настройки сайта (content/settings.json) ----------
SETTINGS_FILE = "content/settings.json"
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def get_settings():
    r = gh_file(SETTINGS_FILE)
    return {"settings": json.loads(base64.b64decode(r["content"]).decode()) if r else {}}


def save_settings(body):
    new = body.get("settings") or {}
    r = gh_file(SETTINGS_FILE)
    cur = json.loads(base64.b64decode(r["content"]).decode()) if r else {}
    out = dict(cur)
    if "hero_image" in new:
        hi = str(new["hero_image"] or "")
        if hi and not re.match(r"^/wp-content/uploads/[\w./%-]+$", hi):
            raise HttpErr(400, "Неверная картинка")
        out["hero_image"] = hi
    if "colors" in new:
        c = {k: v for k, v in (new["colors"] or {}).items() if k in ("ink", "accent", "cta") and HEX.match(str(v))}
        out["colors"] = {**cur.get("colors", {}), **c}
    if "social" in new:
        soc = {}
        for k, v in (new["social"] or {}).items():
            v = str(v or "").strip()
            if k in ("vk", "max", "ok", "dzen", "telegram", "youtube") and (not v or re.match(r"^https://[^\s\"'<>]+$", v)):
                soc[k] = v
        out["social"] = {**cur.get("social", {}), **soc}
    if "programs" in new:
        progs = []
        for g in (new["programs"] or [])[:10]:
            items = [str(x).strip()[:150] for x in (g.get("items") or []) if str(x).strip()][:30]
            name = str(g.get("group", "")).strip()[:80]
            if name and items:
                progs.append({"group": name, "items": items})
        out["programs"] = progs
    if "donate" in new:
        d = new["donate"] or {}
        dd = dict(cur.get("donate", {}))
        for k in ("title", "text"):
            if k in d:
                dd[k] = str(d[k]).strip()[:500]
        if "url" in d:
            u = str(d["url"] or "").strip()
            if u and not re.match(r"^https://[^\s\"'<>]+$", u):
                raise HttpErr(400, "Ссылка на оплату должна начинаться с https://")
            dd["url"] = u
        out["donate"] = dd
    gh_put(SETTINGS_FILE, json.dumps(out, ensure_ascii=False, indent=1).encode(), "Админка: настройки сайта", r["sha"] if r else None)
    return {"ok": True, "settings": out}


# ---------- формы сайта -> почта ----------
def send_form(body):
    c = cfg()
    if body.get("website"):  # поле-ловушка для ботов
        return {"ok": True}
    fields = body.get("fields") or {}
    if not isinstance(fields, dict) or not fields or len(json.dumps(fields)) > 20000:
        raise HttpErr(400, "Пустая форма")
    title = str(body.get("title", "Форма с сайта"))[:120]
    lines = [f"{k}: {v}" for k, v in fields.items()]
    lines += ["", "Страница: " + str(body.get("page", ""))[:300]]
    msg = EmailMessage()
    msg["Subject"] = "Сайт: " + title
    msg["From"] = formataddr(("Сайт helpautism.ru", c["SMTP_USER"]))
    msg["To"] = c["FORMS_TO"] or c["SMTP_USER"]
    reply = next((v for k, v in fields.items() if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(v))), None)
    if reply:
        msg["Reply-To"] = str(reply)
    msg.set_content("\n".join(lines))
    with smtplib.SMTP_SSL("smtp.yandex.ru", 465, context=ssl.create_default_context(), timeout=20) as s:
        s.login(c["SMTP_USER"], c["SMTP_PASSWORD"])
        s.send_message(msg)
    return {"ok": True}


def handler(event, context):
    method = event.get("httpMethod", "GET")
    if method == "OPTIONS":
        return {"statusCode": 204, "headers": CORS, "body": ""}
    q = event.get("queryStringParameters") or {}
    a = q.get("a", "")
    try:
        body = {}
        if event.get("body"):
            raw = event["body"]
            if event.get("isBase64Encoded"):
                raw = base64.b64decode(raw).decode()
            body = json.loads(raw)
        ip = ((event.get("requestContext") or {}).get("identity") or {}).get("sourceIp", "?")
        if a == "login":
            return resp(200, login(body, ip))
        if a == "form":
            return resp(200, send_form(body))
        check_token(event)
        if a == "get":
            return resp(200, get_doc(q))
        if a == "save":
            return resp(200, save_doc(body))
        if a == "delete":
            return resp(200, delete_doc(body))
        if a == "upload":
            return resp(200, upload(body))
        if a == "settings":
            return resp(200, save_settings(body) if body else get_settings())
        if a == "ping":
            return resp(200, {"ok": True})
        raise HttpErr(404, "Неизвестное действие")
    except HttpErr as e:
        return resp(e.code, {"error": e.msg})
    except Exception as e:  # не показываем подробности наружу
        print("ERROR", repr(e))
        return resp(500, {"error": "Ошибка сервера"})
