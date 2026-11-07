#!/usr/bin/env python3
"""
Полное зеркало helpautism.ru из web.archive.org на заданную дату.

  python3 tools/wayback_mirror.py --target 20201020150025 --out archive/2020
  python3 tools/wayback_mirror.py --target 20261011000000 --out archive/latest --html-only

Для каждого адреса сайта берётся снимок, ближайший к --target, и сохраняется
в исходном виде (режим id_, без панели архива). Дополнительно пишутся
archive/cdx.json (все снимки) и <out>/manifest.json (что откуда скачано).
"""
import argparse, concurrent.futures as cf, hashlib, json, os, re, sys, threading, time, urllib.parse, urllib.request

DOMAIN = "helpautism.ru"
UA = "Mozilla/5.0 (helpautism.ru owner restore)"
lock = threading.Lock()


def http(url, tries=3, binary=True):
    delay = 5
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return None
            if i == tries - 1:
                print(f"  ! {e.code} {url}", flush=True); return None
        except Exception as e:
            if i == tries - 1:
                print(f"  ! {e} {url}", flush=True); return None
        time.sleep(delay); delay = min(delay * 2, 60)


def load_cdx(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    rows = []
    for host in (DOMAIN, "www." + DOMAIN):
        q = urllib.parse.urlencode({"url": host, "matchType": "prefix" if host.startswith("www") else "domain",
                                    "output": "json", "fl": "timestamp,original,mimetype,statuscode,length",
                                    "filter": "statuscode:200"})
        data = http("https://web.archive.org/cdx/search/cdx?" + q)
        if data:
            part = json.loads(data.decode("utf-8", "replace") or "[]")
            rows += part[1:]
        if host == DOMAIN:
            break  # matchType=domain уже включает www
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(rows, f)
    return rows


def norm(u):
    p = urllib.parse.urlsplit(u)
    host = p.netloc.lower().split(":")[0]
    q = p.query
    # ?ver=… у css/js не важен
    q = "&".join(x for x in q.split("&") if x and not x.startswith("ver="))
    return host.removeprefix("www."), urllib.parse.unquote(p.path) or "/", q


def local_path(out, host, path, query, mime):
    sub = "" if host == DOMAIN else host + "/"
    if path.endswith("/"):
        path += "index.html"
    elif "html" in mime and not os.path.splitext(path)[1]:
        path += "/index.html"
    if query:
        base, ext = os.path.splitext(path)
        path = f"{base}__{hashlib.md5(query.encode()).hexdigest()[:8]}{ext or '.html'}"
    path = re.sub(r"[<>:\"|?*]", "_", path)
    return os.path.join(out, sub + path.lstrip("/"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="20201020150025")
    ap.add_argument("--out", default="archive/2020")
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--max-bytes", type=int, default=15_000_000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--include", default="", help="регулярка: брать только такие пути")
    ap.add_argument("--exclude", default="", help="регулярка: пропускать такие пути")
    ap.add_argument("--manifest", default="manifest.json")
    a = ap.parse_args()

    rows = load_cdx("archive/cdx.json")
    print(f"Снимков в CDX: {len(rows)}", flush=True)

    # статистика по годам
    years = {}
    for ts, orig, mime, code, ln in rows:
        if "html" in mime:
            years[ts[:4]] = years.get(ts[:4], 0) + 1
    print("HTML-снимков по годам:", dict(sorted(years.items())), flush=True)

    target = int(a.target)
    best = {}
    for ts, orig, mime, code, ln in rows:
        host, path, q = norm(orig)
        if host != DOMAIN and not host.endswith("." + DOMAIN):
            continue
        if a.html_only and "html" not in mime:
            continue
        if re.search(r"^(video|audio)/", mime):
            continue
        if re.search(r"/(wp-json|xmlrpc\.php|wp-login\.php|feed)(/|$)|/comment-page-|replytocom=", path + "?" + q):
            continue
        if a.include and not re.search(a.include, path):
            continue
        if a.exclude and re.search(a.exclude, path):
            continue
        # маленькие html-снимки — заглушка антибота Beget ("beget=begetok"), пропускаем
        if "html" in mime and ln.isdigit() and int(ln) < 1000:
            continue
        key = (host, path, q)
        best.setdefault(key, []).append((abs(int(ts) - target), ts, orig, mime, ln))

    todo = sorted((k, sorted(v)) for k, v in best.items())
    print(f"К скачиванию: {len(todo)} адресов → {a.out}", flush=True)
    manifest, done = {}, [0]
    mpath = os.path.join(a.out, a.manifest)
    if os.path.exists(mpath):
        manifest = json.load(open(mpath))

    def is_stub(b):
        return b is not None and b"beget=begetok" in b[:3000]

    def job(item):
        (host, path, q), cands = item
        d, ts, orig, mime, ln = cands[0]
        dst = local_path(a.out, host, path, q, mime)
        rel = os.path.relpath(dst, a.out)
        if rel in manifest and os.path.exists(dst) and not is_stub(open(dst, "rb").read(3000)):
            return
        if ln and ln.isdigit() and int(ln) > a.max_bytes:
            return
        data = None
        for d, ts, orig, mime, ln in cands[:4]:  # если попалась заглушка — пробуем соседние снимки
            data = http(f"https://web.archive.org/web/{ts}id_/{orig}")
            if data is not None and not is_stub(data):
                break
            data = None
        if data is None:
            return
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(data)
        with lock:
            manifest[rel] = {"url": orig, "timestamp": ts, "mime": mime}
            done[0] += 1
            if done[0] % 25 == 0:
                print(f"  {done[0]} файлов…", flush=True)
                json.dump(manifest, open(mpath, "w"), ensure_ascii=False, indent=1)

    with cf.ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(job, todo))
    os.makedirs(a.out, exist_ok=True)
    json.dump(manifest, open(mpath, "w"), ensure_ascii=False, indent=1)
    print(f"Готово: {len(manifest)} файлов в {a.out}", flush=True)


if __name__ == "__main__":
    main()
