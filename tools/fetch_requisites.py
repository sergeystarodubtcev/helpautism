#!/usr/bin/env python3
"""
Докачивает всё, на что ссылаются уже скачанные страницы archive/2020:
CSS, JS, шрифты, картинки (в т.ч. url() внутри CSS). Повторяет, пока находятся новые файлы.

  python3 tools/fetch_requisites.py --ts 20201020150025 --dir archive/2020
"""
import argparse, concurrent.futures as cf, json, os, re, threading, time, urllib.parse, urllib.request

UA = "Mozilla/5.0 (helpautism.ru owner restore)"
ASSET = re.compile(r"\.(css|js|png|jpe?g|gif|svg|webp|ico|woff2?|ttf|eot|otf|pdf|docx?|xlsx?|pptx?|mp3)$", re.I)
lock = threading.Lock()


def http(url):
    d = 5
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return None
        except Exception:
            pass
        time.sleep(d); d *= 2
    return None


def refs_in(path, text, base_url):
    out = []
    if path.endswith(".css"):
        for r in re.findall(r"url\(\s*['\"]?([^'\")]+)", text) + re.findall(r"@import\s+['\"]([^'\"]+)", text):
            out.append(urllib.parse.urljoin(base_url, r.strip()))
    else:
        for r in re.findall(r"(?:src|href|data-src|data-bg|data-lazy-src|content)=['\"]([^'\"]+)['\"]", text):
            out.append(r)
        for ss in re.findall(r"srcset=['\"]([^'\"]+)", text):
            out += [x.strip().split(" ")[0] for x in ss.split(",")]
        out += re.findall(r"url\(\s*['\"]?([^'\")]+)", text)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default="20201020150025")
    ap.add_argument("--dir", default="archive/2020")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    mpath = os.path.join(a.dir, "manifest-req.json")
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    failed = set(manifest.get("__failed__", []))
    scanned = set()

    def local(u):
        p = urllib.parse.urlsplit(u)
        return os.path.join(a.dir, urllib.parse.unquote(p.path).lstrip("/"))

    def job(u):
        dst = local(u)
        data = http(f"https://web.archive.org/web/{a.ts}id_/{u}")
        with lock:
            if data is None:
                failed.add(u); print("  ! нет", u, flush=True); return
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(data)
            manifest[os.path.relpath(dst, a.dir)] = {"url": u}
            print("  ok", u, flush=True)

    rnd = 0
    while True:
        rnd += 1
        todo = set()
        for d, _, files in os.walk(a.dir):
            for f in files:
                p = os.path.join(d, f)
                if p in scanned or not (f.endswith((".html", ".css"))):
                    continue
                scanned.add(p)
                rel = os.path.relpath(p, a.dir).replace(os.sep, "/")
                base = "http://helpautism.ru/" + rel
                txt = open(p, encoding="utf-8", errors="ignore").read()
                for r in refs_in(p, txt, base):
                    r = r.replace("&amp;", "&").replace("&#038;", "&").strip()
                    if r.startswith("//"):
                        r = "http:" + r
                    r = urllib.parse.urljoin(base, r)
                    sp = urllib.parse.urlsplit(r)
                    if not sp.netloc.lower().endswith("helpautism.ru") or not ASSET.search(sp.path):
                        continue
                    clean = f"http://helpautism.ru{sp.path}"
                    if clean in failed or os.path.exists(local(clean)):
                        continue
                    todo.add(clean)
        # сначала оформление, потом картинки
        order = sorted(todo, key=lambda u: (0 if re.search(r"\.(css|js|woff2?|ttf|eot)$", u) else 1 if "/themes/" in u or "/plugins/" in u else 2, u))
        print(f"Раунд {rnd}: к скачиванию {len(order)}", flush=True)
        if not order:
            break
        with cf.ThreadPoolExecutor(a.workers) as ex:
            list(ex.map(job, order))
        manifest["__failed__"] = sorted(failed)
        json.dump(manifest, open(mpath, "w"), ensure_ascii=False, indent=1)
    print("Готово", flush=True)


if __name__ == "__main__":
    main()
