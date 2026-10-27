"""Install the classifieds app into the XpertCreation project.

Run it from /var/www/xpertcreation-api with the venv active:

    python3 install_classifieds.py

It copies nothing: keep this file and the `classifieds/` folder in that
directory first. It patches settings.py and the root urls.py (idempotently),
adds the /bazaar route to nginx, then seeds the usual categories.
"""

import os
import re
import subprocess
import sys

PROJECT = os.getcwd()
SETTINGS = os.path.join(PROJECT, "xpertapi", "settings.py")
ROOT_URLS = os.path.join(PROJECT, "xpertapi", "urls.py")
NGINX = "/etc/nginx/sites-enabled/xpertcreation-landing"
LANDING = "/var/www/xpertcreation-landing"

CATEGORIES = [
    ("Mobiles", "📱"), ("Vehicles", "🚗"), ("Property", "🏠"),
    ("Electronics", "💻"), ("Home & Furniture", "🛋️"), ("Fashion", "👕"),
    ("Jobs", "💼"), ("Services", "🔧"), ("Pets", "🐾"),
    ("Books & Education", "📚"), ("Sports", "🏏"), ("Everything Else", "📦"),
]


def step(text):
    print("\n==> " + text)


def patch_settings():
    step("settings.py: INSTALLED_APPS")
    s = open(SETTINGS).read()
    if '"classifieds"' in s or "'classifieds'" in s:
        print("    already installed")
        return
    m = re.search(r"INSTALLED_APPS\s*=\s*\[", s)
    if not m:
        print("    !! INSTALLED_APPS nahi mila - manually add karein")
        return
    s = s[:m.end()] + '\n    "classifieds",' + s[m.end():]
    open(SETTINGS, "w").write(s)
    print("    added")


def patch_urls():
    step("urls.py: /api/classifieds/")
    s = open(ROOT_URLS).read()
    if "classifieds.urls" in s:
        print("    already wired")
        return
    if "from django.urls import include" not in s and "include," not in s:
        s = s.replace("from django.urls import path",
                      "from django.urls import include, path", 1)
    m = re.search(r"urlpatterns\s*=\s*\[", s)
    if not m:
        print("    !! urlpatterns nahi mila - manually add karein")
        return
    line = '\n    path("api/classifieds/", include("classifieds.urls")),'
    s = s[:m.end()] + line + s[m.end():]
    open(ROOT_URLS, "w").write(s)
    print("    added")


def patch_nginx():
    step("nginx: /bazaar route")
    if not os.path.exists(NGINX):
        print("    !! config nahi mila, skip")
        return
    s = open(NGINX).read()
    if "bazaar.html" in s:
        print("    already present")
        return
    anchor = "    location = /tools          { try_files /tools.html =404; }"
    if anchor not in s:
        print("    !! anchor nahi mila - manually add karein:")
        print("       location = /bazaar { try_files /bazaar.html =404; }")
        return
    s = s.replace(anchor, anchor + "\n    location = /bazaar         { try_files /bazaar.html =404; }", 1)
    open(NGINX, "w").write(s)
    print("    added")


def seed():
    step("categories seed")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xpertapi.settings")
    import django

    django.setup()
    from classifieds.models import Category

    made = 0
    for i, (name, icon) in enumerate(CATEGORIES):
        _, created = Category.objects.get_or_create(
            name=name, defaults={"icon": icon, "order": i}
        )
        made += 1 if created else 0
    print("    %d nayi categories (total %d)" % (made, Category.objects.count()))


def main():
    if not os.path.exists(os.path.join(PROJECT, "manage.py")):
        sys.exit("manage.py nahi mila - /var/www/xpertcreation-api se chalayein")
    if not os.path.isdir(os.path.join(PROJECT, "classifieds")):
        sys.exit("classifieds/ folder yahan nahi hai - pehle copy karein")

    for f in (SETTINGS, ROOT_URLS):
        subprocess.run(["cp", f, f + ".bak.classifieds"], check=False)

    patch_settings()
    patch_urls()
    patch_nginx()

    step("migrations")
    subprocess.run([sys.executable, "manage.py", "makemigrations", "classifieds"], check=True)
    subprocess.run([sys.executable, "manage.py", "migrate"], check=True)

    seed()

    step("media folder")
    subprocess.run(["mkdir", "-p", os.path.join(PROJECT, "media", "ads")], check=False)
    subprocess.run(["chown", "-R", "www-data:www-data", os.path.join(PROJECT, "media", "ads")],
                   check=False)

    step("baqi kaam")
    print("""    1. bazaar.html ko landing folder mein rakhein:
         cp bazaar.html /var/www/xpertcreation-landing/
    2. nginx test + reload:
         nginx -t && systemctl reload nginx
    3. gunicorn restart:
         systemctl restart gunicorn-academy
    4. test:
         curl -s https://xpertcreation.com/api/classifieds/categories/
         curl -s -o /dev/null -w "%{http_code}\\n" https://xpertcreation.com/bazaar""")


if __name__ == "__main__":
    main()
