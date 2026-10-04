"""Library: free, legal books from Internet Archive, Project Gutenberg and Wikisource, added by staff."""
from django.db.models import F, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Book, SavedBook
from .sources import parse


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _out(b, saved=False):
    return {"id": b.id, "title": b.title, "author": b.author, "year": b.year, "lang": b.lang, "category": b.category, "description": b.description,
            "source": b.source, "url": b.source_url, "cover": b.cover, "rights": b.rights, "views": b.views, "saved": saved,
            "embed": "https://archive.org/embed/" + b.source_id if b.source == "archive" else ""}


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def books(request):
    u = request.user
    if request.method == "GET":
        qs = Book.objects.filter(active=True); g = request.GET
        if g.get("cat") in dict(Book.CATS): qs = qs.filter(category=g["cat"])
        if g.get("lang") in ("ur", "en", "ar"): qs = qs.filter(lang=g["lang"])
        if g.get("q"): qs = qs.filter(Q(title__icontains=g["q"][:60]) | Q(author__icontains=g["q"][:60]))
        if g.get("saved") and u.is_authenticated: qs = qs.filter(id__in=SavedBook.objects.filter(user=u).values("book_id"))
        if g.get("ids"): qs = qs.filter(id__in=[int(x) for x in g["ids"].split(",")[:20] if x.isdigit()])
        qs = qs.order_by("-views", "title") if g.get("sort") == "top" else qs.order_by("-created_at")
        mine = set(SavedBook.objects.filter(user=u).values_list("book_id", flat=True)) if u.is_authenticated else set()
        return Response({"books": [_out(b, b.id in mine) for b in qs[:120]], "cats": [{"key": k, "name": n} for k, n in Book.CATS], "staff": _staff(u)})
    if not _staff(u):
        return Response({"detail": "Only staff can add books."}, status=403)
    try:
        info = parse(request.data.get("url"))
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
    if Book.objects.filter(source=info["source"], source_id=info["source_id"]).exists():
        return Response({"detail": "That book is already in the library."}, status=400)
    cat = request.data.get("category") if request.data.get("category") in dict(Book.CATS) else "urdu"
    for k in ("title", "author"):
        if str(request.data.get(k) or "").strip(): info[k] = str(request.data[k]).strip()[:200 if k == "title" else 160]
    b = Book.objects.create(category=cat, added_by=u, **info)
    return Response(_out(b), status=201)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([AllowAny])
def book(request, pk):
    u = request.user; b = Book.objects.filter(pk=pk).first()
    if not b or (not b.active and not _staff(u)):
        return Response({"detail": "Book not found."}, status=404)
    if request.method == "GET":
        Book.objects.filter(pk=pk).update(views=F("views") + 1)
        return Response(dict(_out(b, u.is_authenticated and SavedBook.objects.filter(user=u, book=b).exists()), staff=_staff(u)))
    if request.method == "POST" and request.data.get("action") == "save":
        if not u.is_authenticated:
            return Response({"detail": "Sign in to save books."}, status=401)
        o = SavedBook.objects.filter(user=u, book=b).first()
        if o: o.delete(); return Response({"saved": False})
        SavedBook.objects.create(user=u, book=b); return Response({"saved": True})
    if not _staff(u):
        return Response({"detail": "Staff only."}, status=403)
    if request.method == "DELETE":
        b.delete(); return Response({"deleted": True})
    for k in ("title", "author", "description"):
        if k in request.data: setattr(b, k, str(request.data[k])[:600 if k == "description" else 200])
    if request.data.get("category") in dict(Book.CATS): b.category = request.data["category"]
    if "active" in request.data: b.active = bool(request.data["active"])
    b.save(); return Response(_out(b))
