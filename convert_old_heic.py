#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Convert the donation photos already sitting on disk as HEIC.

Run from /var/www/xpertcreation-api with the venv python:

    ./venv/bin/python convert_old_heic.py --dry-run
    ./venv/bin/python convert_old_heic.py

The original .heic is renamed to .heic.old rather than deleted, so this can
be undone. The database row is repointed at the new .jpg.
"""

import io
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xpertapi.settings")
django.setup()

from django.conf import settings                      # noqa: E402
from donations.models import DonationPhoto            # noqa: E402

DRY = "--dry-run" in sys.argv
MAX_SIDE = 1600

from PIL import Image, ImageOps                       # noqa: E402
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    print("pillow-heif is not installed in this venv:")
    print("  ./venv/bin/pip install pillow-heif")
    sys.exit(1)


def convert(path):
    """HEIC in, upright JPEG out. Returns the new path."""
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    if im.mode not in ("RGB", "L"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        im = im.convert("RGBA")
        bg.paste(im, mask=im.split()[3])
        im = bg
    elif im.mode == "L":
        im = im.convert("RGB")
    if max(im.size) > MAX_SIDE:
        r = MAX_SIDE / float(max(im.size))
        im = im.resize((max(1, int(im.size[0] * r)), max(1, int(im.size[1] * r))),
                       Image.LANCZOS)
    out = os.path.splitext(path)[0] + ".jpg"
    n = 1
    while os.path.exists(out):                    # never clobber a real photo
        out = "%s_c%d.jpg" % (os.path.splitext(path)[0], n)
        n += 1
    im.save(out, "JPEG", quality=85, optimize=True)
    return out


def main():
    rows = [p for p in DonationPhoto.objects.all()
            if p.image and p.image.name.lower().endswith((".heic", ".heif"))]

    if not rows:
        print("No HEIC photos in the database. Nothing to do.")
        return 0

    print("%s %d HEIC photo(s)\n" % ("Would convert" if DRY else "Converting", len(rows)))
    done = failed = 0

    for p in rows:
        old_name = p.image.name
        old_path = os.path.join(str(settings.MEDIA_ROOT), old_name)
        print("  item %s  %s" % (p.item_id, old_name))

        if not os.path.exists(old_path):
            print("     !! file missing on disk, row left alone")
            failed += 1
            continue

        if DRY:
            print("     would write %s and repoint the row"
                  % (os.path.splitext(old_name)[0] + ".jpg"))
            done += 1
            continue

        try:
            new_path = convert(old_path)
        except Exception as e:
            print("     !! could not convert: %s" % e)
            failed += 1
            continue

        new_name = os.path.relpath(new_path, str(settings.MEDIA_ROOT)).replace(os.sep, "/")
        p.image.name = new_name
        p.save(update_fields=["image"])
        os.rename(old_path, old_path + ".old")     # keep it, do not delete
        print("     -> %s  (%d KB)" % (new_name, os.path.getsize(new_path) // 1024))
        done += 1

    print("\n%s: %d, failed: %d" % ("Would convert" if DRY else "Converted", done, failed))
    if not DRY and done:
        print("\nThe originals are kept beside the new files as .heic.old.")
        print("Once the photos look right on the site you can remove them:")
        print("  find %s -name '*.heic.old' -delete" % settings.MEDIA_ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())

