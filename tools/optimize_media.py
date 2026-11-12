#!/usr/bin/env python3
"""
Сжатие медиафайлов для сайта.

  python3 tools/optimize_media.py <папка_с_исходниками> media/

- картинки уменьшаются до 1600 px по длинной стороне;
- JPEG пересжимается (качество 80, progressive);
- PNG без прозрачности весом больше 250 КБ переводится в JPEG
  (новое имя «файл.png.jpg», замены записываются в media/renames.json — сборщик подставляет их в ссылки);
- файлы больше 25 МБ (длинные видео) пропускаются и перечисляются в media/skipped.txt —
  их нужно положить в облачное хранилище отдельно.
"""
import json, os, shutil, sys
from PIL import Image, ImageOps

MAX_SIDE = 1600
MAX_FILE = 25 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 200_000_000


def has_alpha(im):
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        a = im.convert("RGBA").getchannel("A")
        return a.getextrema()[0] < 250
    return False


def main():
    src, dst = sys.argv[1], sys.argv[2]
    renames, skipped = {}, []
    before = after = 0
    for d, _, files in os.walk(src):
        for f in files:
            sp = os.path.join(d, f)
            rel = os.path.relpath(sp, src).replace(os.sep, "/")
            size = os.path.getsize(sp)
            before += size
            if size > MAX_FILE:
                skipped.append(f"/{rel}\t{size // (1024 * 1024)} МБ")
                continue
            dp = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(dp), exist_ok=True)
            ext = f.lower().rsplit(".", 1)[-1]
            try:
                if ext in ("jpg", "jpeg", "png", "webp"):
                    im = Image.open(sp)
                    im = ImageOps.exif_transpose(im)
                    if max(im.size) > MAX_SIDE:
                        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
                    if ext in ("jpg", "jpeg"):
                        im.convert("RGB").save(dp, "JPEG", quality=80, optimize=True, progressive=True)
                    elif ext == "webp":
                        im.save(dp, "WEBP", quality=80)
                    else:
                        if not has_alpha(im) and size > 250 * 1024:
                            dp2 = dp + ".jpg"
                            im.convert("RGB").save(dp2, "JPEG", quality=82, optimize=True, progressive=True)
                            renames["/" + rel] = "/" + rel + ".jpg"
                            dp = dp2
                        else:
                            im.save(dp, "PNG", optimize=True)
                    if os.path.getsize(dp) > size and not dp.endswith(".png.jpg"):
                        shutil.copy2(sp, dp)  # пересжатие не помогло — оставляем исходник
                else:
                    shutil.copy2(sp, dp)
            except Exception as e:
                print("! ", rel, e)
                shutil.copy2(sp, dp)
            after += os.path.getsize(dp)
    with open(os.path.join(dst, "renames.json"), "w") as fh:
        json.dump(renames, fh, ensure_ascii=False, indent=0)
    with open(os.path.join(dst, "skipped.txt"), "w") as fh:
        fh.write("\n".join(skipped) + "\n")
    print(f"Было {before / 1e6:.0f} МБ, стало {after / 1e6:.0f} МБ; PNG→JPEG: {len(renames)}; пропущено больших: {len(skipped)}")


if __name__ == "__main__":
    main()
