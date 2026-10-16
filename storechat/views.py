"""Store chat API (/api/storechat/).
shop/<slug>/?p=ID   public: shop name, online now?, greeting, quick question buttons
thread/             buyer: GET ?shop=slug&since=id messages; POST {shop, product, text | k} send (auto-reply answers at once)
mine/               buyer: my chats with shops
inbox/              seller: my shop's chats;  inbox/<id>/ GET messages, POST {text, save} reply (save = keep as auto-reply)
faqs/               seller: GET / POST auto-replies (bot on/off, greeting, away message, questions and answers)
unread/             counts for badges
Free: no AI. Answers come from the shop's own questions and answers and from the product details."""
import re
import time

from django.core.cache import cache
from django.db.models import F, Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from store.models import Merchant, Product

from .models import Bot, Faq, Msg, Thread

ONLINE = 150          # seller counts as online this many seconds after they last opened their chats
MAXFAQ = 40


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _txt(v, n):
    return re.sub(r"[ \t]+", " ", str(v or "")).strip()[:n]


def _rs(n):
    return "Rs {:,}".format(int(n or 0))


def _int(v):
    try:
        return int(v)
    except Exception:
        return 0


def _name(u):
    return ((getattr(u, "full_name", "") or u.username or "Buyer").strip())[:40]


def _notify(user, text, link):
    try:
        from notifications.views import notify
        notify(user, "store", text, link)
    except Exception:
        pass


def _seen(m):
    cache.set("sc:on:%d" % m.id, int(time.time()), ONLINE)


def _online(m):
    return bool(cache.get("sc:on:%d" % m.id))


def _bot(m):
    b, made = Bot.objects.get_or_create(merchant=m)
    if made and not Faq.objects.filter(merchant=m).exists():
        for i, (q, k, a, on) in enumerate(SEED):
            Faq.objects.create(merchant=m, q=q, keys=k, a=a, on=on, pos=i)
    return b


def _myshop(u):
    return Merchant.objects.filter(user=u, status="approved").first()


# Ready-made questions every shop starts with. The ones about the shop's own policy start OFF: the seller checks
# the answer, changes it if needed, and turns it on. The ones about how XpertCreation works start ON.
SEED = [
    ("How do I order?", "order kaise, kaise order, how to order, order karna, buy kaise, kharidna",
     "Open the product, tap Buy now (or Add to cart), then give your name, phone and address. You can follow the order in My orders.", True),
    ("How can I track my order?", "track, tracking, kahan hai order, order status, parcel",
     "When the shop ships it, the courier name and tracking number show in My orders on the Store page.", True),
    ("Is my money safe if I pay online?", "safe, secure, trust, fraud, dhoka, bharosa",
     "Yes. When you pay online, XpertCreation holds the money and the shop is paid only after you receive your order.", True),
    ("Is it original?", "original, genuine, asli, copy, fake, replica, first copy",
     "Yes, we sell original products. Check the photos, the description and reviews from verified buyers.", False),
    ("Return or exchange?", "return, wapis, wapas, exchange, change, refund, badal",
     "If something is wrong, tell us within 3 days of delivery from My orders and we will sort it out.", False),
    ("Warranty?", "warranty, guarantee, guaranty",
     "Ask us about the warranty for this product and we will tell you.", False),
    ("Other colour or size?", "colour, color, rang, size, saiz, small, medium, large, xl",
     "Tell us the colour or size you want and we will check if we have it.", False),
    ("Shop timings?", "timing, time, open, khula, band, closed, hours",
     "We reply to messages from 10 am to 8 pm, every day except Sunday.", False),
]

# Built-in answers from the product and shop details: no setup needed.
BUILT = [
    ("price", "Price?", ["price", "prise", "qeemat", "qimat", "keemat", "kimat", "kitne ka", "kitnay ka", "kitne ki", "kitny ka", "kitne mein", "rate", "cost", "discount", "last price"]),
    ("delivery", "Delivery time and charges?", ["delivery", "deliver", "shipping", "ship", "kab tak", "kitne din", "kitnay din", "pohanch", "pahunch", "courier", "charges"]),
    ("cod", "Cash on delivery?", ["cod", "cash on delivery", "cash", "nakad"]),
    ("stock", "Is it in stock?", ["stock", "available", "availability", "mojood", "maujood", "mil jaye", "milay ga", "milega", "mil sakta", "left"]),
    ("pay", "How can I pay?", ["pay", "payment", "card", "jazzcash", "easypaisa", "wallet", "bank"]),
    ("bulk", "Wholesale / bulk price?", ["wholesale", "bulk", "dozen", "darjan", "carton", "moq"]),
    ("where", "Where is the shop?", ["where", "kahan", "kaha", "location", "address", "city", "shehar"]),
    ("hello", "", ["hi", "hello", "salam", "assalam", "assalamualaikum", "aoa", "asalam", "slam", "hey"]),
]
BUILT_Q = {k: q for k, q, _ in BUILT}
STOP = set(("the a an is are am i you me my your it this that to of for and or in on at do does can will what how when "
            "where which kya hai hain ka ki ke ko se me mein main aap ap tum yeh ye wo woh kar karo karna ho hy he plz "
            "please sir bhai ji").split())


def _norm(s):
    return " " + re.sub(r"\s+", " ", re.sub(r"[^\w\s؀-ۿ]+", " ", (s or "").lower())).strip() + " "


def _hits(t, keys):
    return sum(1 for k in keys if k and (" " + k.strip() + " ") in t)


def _built(key, m, p):
    b = _bot(m)
    if key == "hello":
        return b.greeting or ("Wa alaikum assalam! Welcome to %s. Ask about price, delivery, cash on delivery or stock, or type your question." % m.name)
    if key == "where":
        return "%s is in %s and delivers across Pakistan." % (m.name, m.city) if not p else "%s ships from %s." % (m.name, m.city)
    if not p:
        if key in ("price", "stock", "bulk"):
            return "Prices and stock are shown on each product. Open a product and tap Chat with seller to ask about it."
        if key == "cod":
            return ("Many of our products have cash on delivery - look for COD on the product." if m.products.filter(active=True, cod=True).exists()
                    else "Our products are paid online. XpertCreation holds the money until you receive your order.")
        if key == "delivery":
            return "Each product shows its delivery days and fee. %s ships from %s." % (m.name, m.city)
        if key == "pay":
            return "You can pay cash on delivery where a product shows COD, or online by card or wallet."
    if key == "price":
        s = "%s is %s." % (p.title, _rs(p.price))
        if p.old_price > p.price:
            s = "%s is %s (was %s, %d%% off)." % (p.title, _rs(p.price), _rs(p.old_price), round((p.old_price - p.price) * 100.0 / p.old_price))
        return s + (" Delivery fee %s." % _rs(p.delivery_fee) if p.delivery_fee else " Free delivery.")
    if key == "delivery":
        return "Delivery in %d day%s, %s. Ships from %s." % (p.delivery_days, "" if p.delivery_days == 1 else "s",
                                                            "fee " + _rs(p.delivery_fee) if p.delivery_fee else "free delivery", m.city)
    if key == "cod":
        return ("Yes, cash on delivery is available for this product." if p.cod
                else "This product is paid online (card or wallet). XpertCreation holds the money until you receive your order.")
    if key == "stock":
        return ("Yes, it is in stock (%d left)." % p.stock) if p.stock > 0 else "Sorry, it is out of stock right now. The seller will reply if more is coming."
    if key == "pay":
        w = [x for x, ok in (("cash on delivery", p.cod), ("online by card or wallet", p.online)) if ok]
        return "You can pay " + (" or ".join(w) if w else "as shown at checkout") + "."
    if key == "bulk":
        if p.wholesale_price and p.moq:
            return "Wholesale: %s per unit for %d or more. For a bigger order, tap Request a quote on the product." % (_rs(p.wholesale_price), p.moq)
        return "There is no wholesale price on this product yet. Tell us the quantity and the seller will reply."
    return ""


def _answer(m, p, text):
    """The auto-reply for a message, or "" when the seller should answer."""
    t = _norm(text)
    words = set(w for w in t.split() if len(w) >= 3 and w not in STOP)
    best, score = None, 0
    for f in Faq.objects.filter(merchant=m, on=True):
        s = 2 * _hits(t, [k.lower() for k in f.keys.split(",")])
        qw = set(w for w in _norm(f.q).split() if len(w) >= 3 and w not in STOP)
        if qw:
            s += len(qw & words)
            if len(qw & words) == len(qw):
                s += 1
        if s > score:
            best, score = f, s
    if best and score >= 2:
        return best.a
    found = [(k, _hits(t, ks)) for k, _, ks in BUILT]
    found = [x for x in found if x[1]]
    if not found:
        return ""
    real = [k for k, n in sorted(found, key=lambda x: -x[1]) if k != "hello"]
    keys = real[:3] if real else ["hello"]
    return "\n".join(_built(k, m, p) for k in keys)


def _quick(m, p):
    b = ["price", "delivery", "cod", "stock"] if p else ["delivery", "cod", "where"]
    q = [{"k": "b:" + k, "q": BUILT_Q[k]} for k in b]
    q += [{"k": "f:%d" % f.id, "q": f.q} for f in Faq.objects.filter(merchant=m, on=True)[:8]]
    return q


def _m(x):
    return {"id": x.id, "who": x.who, "text": x.text, "when": x.created_at.isoformat(), "product": x.product_id, "open": x.open}


def _shop(slug):
    return Merchant.objects.filter(slug=slug, status="approved").first()


def _prod(m, pid):
    return Product.objects.filter(pk=_int(pid), merchant=m).first() if _int(pid) else None


@api_view(["GET"])
@permission_classes([AllowAny])
def shop_info(request, slug):
    m = _shop(slug)
    if not m:
        return _err("Shop not found.", 404)
    p = _prod(m, request.GET.get("p"))
    b = _bot(m)
    u = request.user
    return Response({"shop": {"name": m.name, "slug": m.slug, "city": m.city, "logo": ("/media/" + m.logo) if m.logo else ""},
                     "online": _online(m), "bot": b.on, "quick": _quick(m, p) if b.on else [],
                     "greeting": b.greeting or ("Assalam o alaikum! Welcome to %s. How can we help?" % m.name),
                     "me": bool(u.is_authenticated), "mine": bool(u.is_authenticated and m.user_id == u.pk)})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def thread(request):
    u, d = request.user, request.data
    m = _shop((d.get("shop") if request.method == "POST" else request.GET.get("shop")) or "")
    if not m:
        return _err("Shop not found.", 404)
    if request.method == "GET":
        if not u.is_authenticated:
            return Response({"msgs": [], "login": True, "online": _online(m)})
        t = Thread.objects.filter(merchant=m, buyer=u).first()
        if not t:
            return Response({"msgs": [], "online": _online(m)})
        if t.buyer_unread:
            Thread.objects.filter(pk=t.pk).update(buyer_unread=0)
        qs = t.msgs.filter(id__gt=_int(request.GET.get("since"))) if request.GET.get("since") else t.msgs.all()
        return Response({"msgs": [_m(x) for x in list(qs.order_by("-id")[:80])[::-1]], "online": _online(m)})
    # send
    if u.is_authenticated and m.user_id == u.pk:
        return _err("This is your own shop.")
    p = _prod(m, d.get("product"))
    b = _bot(m)
    k, text = str(d.get("k") or ""), _txt(d.get("text"), 1000)
    reply = ""
    if k.startswith("b:") and k[2:] in BUILT_Q:
        text, reply = BUILT_Q[k[2:]], _built(k[2:], m, p)
    elif k.startswith("f:"):
        f = Faq.objects.filter(merchant=m, pk=_int(k[2:]), on=True).first()
        if f:
            text, reply = f.q, f.a
    elif text and b.on:
        reply = _answer(m, p, text)
    if not text:
        return _err("Type a message.")
    if not b.on:
        reply = ""
    if not u.is_authenticated:
        # Not signed in: auto-replies still answer, nothing is saved. A question for the seller needs sign-in.
        out = [{"id": 0, "who": "buyer", "text": text, "when": "", "product": p.id if p else None}]
        if reply:
            out.append({"id": 0, "who": "bot", "text": reply, "when": "", "product": None})
        return Response({"msgs": out, "login": not reply})
    rk = "sc:rate:%d" % u.pk
    n = cache.get(rk, 0)
    if n >= 20:
        return _err("Too many messages. Wait a minute and try again.", 429)
    cache.set(rk, n + 1, 60)
    t, _ = Thread.objects.get_or_create(merchant=m, buyer=u)
    new = [Msg.objects.create(thread=t, who="buyer", text=text, product_id=p.id if p else None, open=not reply)]
    if reply:
        new.append(Msg.objects.create(thread=t, who="bot", text=reply))
    elif b.on and not cache.get("sc:away:%d" % t.id):
        cache.set("sc:away:%d" % t.id, 1, 1800)
        new.append(Msg.objects.create(thread=t, who="bot", text=(
            "The seller is online and will reply here in a moment." if _online(m) else
            (b.away or "Thanks! The seller will reply here soon. You will get a notification."))))
    if p:
        t.product = p
    t.last = text[:200]
    t.seller_unread = F("seller_unread") + 1
    t.save()
    if not reply and not cache.get("sc:ntf:%d" % t.id):
        cache.set("sc:ntf:%d" % t.id, 1, 600)
        _notify(m.user, "Chat from %s: %s" % (_name(u), text[:80]), "/store#seller-chats")
    return Response({"msgs": [_m(x) for x in new], "online": _online(m)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mine(request):
    ts = Thread.objects.filter(buyer=request.user).select_related("merchant", "product")[:60]
    return Response({"chats": [{"id": t.id, "shop": {"name": t.merchant.name, "slug": t.merchant.slug, "logo": ("/media/" + t.merchant.logo) if t.merchant.logo else ""},
                                "last": t.last, "when": t.updated_at.isoformat(), "unread": t.buyer_unread, "online": _online(t.merchant),
                                "product": {"id": t.product_id, "title": t.product.title} if t.product else None} for t in ts]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inbox(request):
    m = _myshop(request.user)
    if not m:
        return _err("You do not have an approved shop.", 403)
    _seen(m)
    _bot(m)
    ts = Thread.objects.filter(merchant=m).select_related("buyer", "product")[:100]
    return Response({"chats": [{"id": t.id, "buyer": _name(t.buyer), "last": t.last, "when": t.updated_at.isoformat(), "unread": t.seller_unread,
                                "product": {"id": t.product_id, "title": t.product.title} if t.product else None} for t in ts],
                     "unread": Thread.objects.filter(merchant=m).aggregate(s=Sum("seller_unread"))["s"] or 0})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def inbox_thread(request, pk):
    m = _myshop(request.user)
    t = Thread.objects.filter(pk=pk, merchant=m).select_related("buyer").first() if m else None
    if not t:
        return _err("Chat not found.", 404)
    _seen(m)
    if request.method == "GET":
        if t.seller_unread:
            Thread.objects.filter(pk=t.pk).update(seller_unread=0)
        qs = t.msgs.filter(id__gt=_int(request.GET.get("since"))) if request.GET.get("since") else t.msgs.all()
        return Response({"buyer": _name(t.buyer), "msgs": [_m(x) for x in list(qs.order_by("-id")[:120])[::-1]]})
    text = _txt(request.data.get("text"), 1000)
    if not text:
        return _err("Type a reply.")
    sv = _int(request.data.get("save"))
    last_q = t.msgs.filter(who="buyer", pk=sv).first() if sv else None
    x = Msg.objects.create(thread=t, who="seller", text=text)
    t.last = ("You: " + text)[:200]
    t.buyer_unread = F("buyer_unread") + 1
    t.seller_unread = 0
    t.save()
    t.msgs.filter(who="buyer", open=True).update(open=False)
    saved = False
    if last_q and Faq.objects.filter(merchant=m).count() < MAXFAQ:
        Faq.objects.create(merchant=m, q=last_q.text[:160], keys="", a=text, on=True, pos=200)
        saved = True
    if not cache.get("sc:bn:%d" % t.id):
        cache.set("sc:bn:%d" % t.id, 1, 300)
        _notify(t.buyer, "%s replied: %s" % (m.name, text[:80]), "/store#chat-" + m.slug)
    return Response({"msgs": [_m(x)], "saved": saved})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def faqs(request):
    m = _myshop(request.user)
    if not m:
        return _err("You do not have an approved shop.", 403)
    b = _bot(m)
    if request.method == "POST":
        d = request.data
        bd = d.get("bot") if isinstance(d.get("bot"), dict) else {}
        b.on = bool(bd.get("on", b.on))
        b.greeting = _txt(bd.get("greeting"), 300)
        b.away = _txt(bd.get("away"), 300)
        b.save()
        rows = d.get("faqs") if isinstance(d.get("faqs"), list) else None
        if rows is not None:
            clean = []
            for r in rows[:MAXFAQ]:
                if not isinstance(r, dict):
                    continue
                q, a = _txt(r.get("q"), 160), str(r.get("a") or "").strip()[:1000]
                if q and a:
                    clean.append((q, _txt(r.get("keys"), 300), a, bool(r.get("on", True))))
            Faq.objects.filter(merchant=m).delete()
            for i, (q, k, a, on) in enumerate(clean):
                Faq.objects.create(merchant=m, q=q, keys=k, a=a, on=on, pos=i)
    return Response({"bot": {"on": b.on, "greeting": b.greeting, "away": b.away},
                     "faqs": [{"id": f.id, "q": f.q, "keys": f.keys, "a": f.a, "on": f.on} for f in Faq.objects.filter(merchant=m)],
                     "built": [q for k, q, _ in BUILT if q]})


@api_view(["GET"])
@permission_classes([AllowAny])
def unread(request):
    u = request.user
    if not u.is_authenticated:
        return Response({"buyer": 0, "seller": 0})
    m = _myshop(u)
    if m:
        _seen(m)
    return Response({"buyer": Thread.objects.filter(buyer=u).aggregate(s=Sum("buyer_unread"))["s"] or 0,
                     "seller": (Thread.objects.filter(merchant=m).aggregate(s=Sum("seller_unread"))["s"] or 0) if m else 0})


@api_view(["GET"])
@permission_classes([AllowAny])
def directory(request):
    """Yellow pages: every approved shop, A to Z, with search and city filter."""
    from django.db.models import Count, Q
    q, city = _txt(request.GET.get("q"), 60), _txt(request.GET.get("city"), 60)
    qs = Merchant.objects.filter(status="approved")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(about__icontains=q) | Q(products__title__icontains=q)).distinct()
    if city:
        qs = qs.filter(city__iexact=city)
    qs = qs.annotate(n=Count("products", filter=Q(products__active=True, products__hidden=False), distinct=True)).order_by("name")
    cities = list(Merchant.objects.filter(status="approved").exclude(city="").values_list("city", flat=True).distinct().order_by("city")[:200])
    return Response({"cities": cities, "shops": [{
        "name": m.name, "slug": m.slug, "city": m.city, "kind": m.kind, "about": (m.about or "")[:140], "logo": ("/media/" + m.logo) if m.logo else "",
        "rating": round(m.rating_sum / m.rating_n, 1) if m.rating_n else None, "ratings": m.rating_n, "products": m.n, "online": _online(m)} for m in qs[:500]]})
