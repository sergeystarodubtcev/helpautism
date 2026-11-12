#!/usr/bin/env python3
"""Подставляет новые имена сжатых файлов (media/renames.json: PNG -> JPEG) прямо в content/*.json."""
import json, os, re, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ren = json.load(open(os.path.join(ROOT, "media", "renames.json")))
changed = 0
for d, _, files in os.walk(os.path.join(ROOT, "content")):
    for f in files:
        if not f.endswith(".json") or f in ("site.json", "forms.json"):
            continue
        p = os.path.join(d, f)
        doc = json.load(open(p, encoding="utf-8"))
        before = json.dumps(doc, ensure_ascii=False)
        fix = lambda u: ren.get(urllib.parse.unquote(u), u)
        doc["content"] = re.sub(r"/wp-content/uploads/[^\s\"'<>)?#]+", lambda m: fix(m.group(0)), doc.get("content", ""))
        doc["thumbnail"] = fix(doc.get("thumbnail", "")) if doc.get("thumbnail") else ""
        doc["gallery"] = [fix(u) for u in doc.get("gallery", [])]
        if json.dumps(doc, ensure_ascii=False) != before:
            json.dump(doc, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            changed += 1
print("Обновлено файлов:", changed)
