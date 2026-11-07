#!/usr/bin/env python3
"""
Скачивает шрифты Google, которые использовал сайт, в assets/fonts/
(для размещения на российских серверах без обращений к Google).

  python3 tools/fetch_fonts.py
"""
import os, re, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "fonts")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
FAMILIES = [
    "Montserrat:700",
    "Open+Sans:300,300italic,400,400italic,600,600italic,700,700italic,800,800italic",
    "Oswald:300,400",
    "Roboto:400,700",
]


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read()


def main():
    os.makedirs(OUT, exist_ok=True)
    css_all = []
    for fam in FAMILIES:
        css = get(f"https://fonts.googleapis.com/css?family={fam}&subset=cyrillic,cyrillic-ext,latin,latin-ext&display=swap").decode()
        def dl(m):
            url = m.group(1)
            name = re.sub(r"[^\w.-]", "_", url.split("/s/")[-1])
            path = os.path.join(OUT, name)
            if not os.path.exists(path):
                open(path, "wb").write(get(url))
            return f"url({name})"
        css_all.append(re.sub(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", dl, css))
    open(os.path.join(OUT, "fonts.css"), "w").write("\n".join(css_all))
    print("Шрифтов:", len([f for f in os.listdir(OUT) if not f.endswith(".css")]))


if __name__ == "__main__":
    main()
