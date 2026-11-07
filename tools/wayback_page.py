#!/usr/bin/env python3
"""
Скачивает страницы helpautism.ru из web.archive.org вместе со всеми ресурсами
(CSS, JS, шрифты, картинки, url() внутри CSS) на заданную дату.

  python3 tools/wayback_page.py --ts 20201020150025 --out archive/probe / /kontakty/
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

UA = "Mozilla/5.0 (helpautism.ru owner restore)"
DOMAIN = "helpautism.ru"
seen = {}


def http(url, tries=5):
    d = 3
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90) as r:
                return r.read(), r.geturl()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, url
        except Exception:
            pass
        time.sleep(d); d *= 2
    return None, url


def local(out, u):
    p = urllib.parse.urlsplit(u)
    host = p.netloc.lower().removeprefix("www.")
    path = urllib.parse.unquote(p.path) or "/"
    if path.endswith("/"):
        path += "index.html"
    base = "" if host == DOMAIN else "_ext/" + host + "/"
    return os.path.join(out, base + path.lstrip("/"))


def fetch(ts, u, out, depth=0):
    u = urllib.parse.urljoin("https://" + DOMAIN + "/", u.split("#")[0])
    if not u.startswith("http") or u in seen:
        return seen.get(u)
    seen[u] = None
    data, final = http(f"https://web.archive.org/web/{ts}id_/{u}")
    if data is None:
        print("  ! нет:", u, flush=True); return None
    dst = local(out, u)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(data)
    seen[u] = dst
    m = re.search(r"/web/(\d{14})", final)
    print(f"  ok {m.group(1) if m else ''} {u}", flush=True)
    if depth > 3:
        return dst
    text = data.decode("utf-8", "ignore")
    refs = []
    if dst.endswith(".html") or "<html" in text[:2000].lower():
        refs += re.findall(r'<link[^>]+href=["\']([^"\']+)', text)
        refs += re.findall(r'<script[^>]+src=["\']([^"\']+)', text)
        refs += re.findall(r'<img[^>]+src=["\']([^"\']+)', text)
        refs += re.findall(r'data-(?:src|bg|lazy-src)=["\']([^"\']+)', text)
        for ss in re.findall(r'srcset=["\']([^"\']+)', text):
            refs += [x.strip().split(" ")[0] for x in ss.split(",")]
        refs += re.findall(r'url\(\s*["\']?([^"\')]+)', text)
    elif dst.endswith(".css"):
        refs += [urllib.parse.urljoin(u, r) for r in re.findall(r'url\(\s*["\']?([^"\')]+)', text)]
        refs += [urllib.parse.urljoin(u, r) for r in re.findall(r'@import\s+["\']([^"\']+)', text)]
    for r in refs:
        r = r.strip().replace("&amp;", "&")
        if r.startswith(("data:", "javascript:", "mailto:", "tel:", "#")):
            continue
        r = urllib.parse.urljoin(u, r)
        host = urllib.parse.urlsplit(r).netloc.lower()
        # ресурсы сайта и шрифты/стили с внешних CDN
        if DOMAIN in host or "fonts.googleapis" in host or "fonts.gstatic" in host or r.endswith((".css", ".woff", ".woff2", ".ttf")):
            if re.search(r"\.(php)(\?|$)", r) and "load-styles" not in r:
                continue
            fetch(ts, r, out, depth + 1)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default="20201020150025")
    ap.add_argument("--out", default="archive/probe")
    ap.add_argument("pages", nargs="*", default=["/"])
    a = ap.parse_args()
    for p in a.pages:
        print("Страница", p, flush=True)
        fetch(a.ts, p, a.out)
    os.makedirs(a.out, exist_ok=True)
    json.dump({k: v for k, v in seen.items()}, open(os.path.join(a.out, "files.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
