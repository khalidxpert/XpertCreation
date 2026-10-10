"""XpertCreation Store: merchants (B2C and B2B) sell products.
Merchants apply with a verified ID; the team approves. Tiers decide how many products a shop can list:
Bronze (free) 10, Gold 100, Platinum 1,000 (+ featured shop). Gold / Platinum are monthly items on the Promote page.
Buyers pay cash on delivery or online (Safepay, held until the order is completed); merchants can also offer
wholesale prices with a minimum order quantity and answer quote requests (B2B)."""
from django.conf import settings
from django.db import models

CATS = [("mobiles", "Mobiles & tablets"), ("electronics", "Electronics"), ("fashion_w", "Women's fashion"), ("fashion_m", "Men's fashion"),
        ("home", "Home & kitchen"), ("beauty", "Beauty & health"), ("grocery", "Grocery"), ("baby", "Baby & toys"),
        ("sports", "Sports & outdoors"), ("books", "Books & stationery"), ("auto", "Car & bike"), ("industrial", "Business & industrial"),
        ("other", "Other")]


class Merchant(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="merchant")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True)
    kind = models.CharField(max_length=4, default="b2c")              # b2c | b2b | both
    city = models.CharField(max_length=60)
    address = models.CharField(max_length=200, blank=True, default="")
    phone = models.CharField(max_length=20)
    about = models.TextField(max_length=2000, blank=True, default="")
    logo = models.CharField(max_length=200, blank=True, default="")   # path under /media/store/
    status = models.CharField(max_length=10, default="pending", db_index=True)   # pending | approved | rejected | suspended
    note = models.CharField(max_length=300, blank=True, default="")
    rating_sum = models.PositiveIntegerField(default=0)
    rating_n = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class Product(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=12, choices=CATS, default="other", db_index=True)
    description = models.TextField(max_length=6000)
    price = models.PositiveIntegerField()                              # rupees, retail
    old_price = models.PositiveIntegerField(default=0)                 # crossed-out price (0 = none)
    stock = models.PositiveIntegerField(default=1)
    images = models.JSONField(default=list, blank=True)
    cod = models.BooleanField(default=True)                            # cash on delivery
    online = models.BooleanField(default=False)                        # pay online through XpertCreation
    delivery_fee = models.PositiveIntegerField(default=0)
    delivery_days = models.PositiveSmallIntegerField(default=3)
    sku = models.CharField(max_length=40, blank=True, default="")      # merchant's own code
    cost_price = models.PositiveIntegerField(default=0)                # what the merchant pays per unit (private)
    reorder_level = models.PositiveIntegerField(default=0)             # warn when stock falls to this
    wholesale_price = models.PositiveIntegerField(default=0)           # B2B per-unit price (0 = no wholesale)
    moq = models.PositiveIntegerField(default=0)                       # minimum order quantity for wholesale
    active = models.BooleanField(default=True, db_index=True)
    hidden = models.BooleanField(default=False, db_index=True)         # hidden by the team
    sold = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    rating_sum = models.PositiveIntegerField(default=0)
    rating_n = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-id"]


class Order(models.Model):
    """placed (cash on delivery) or pending (online, not paid yet) -> confirmed -> shipped -> delivered -> completed.
    Side roads: cancelled, disputed, refund_due -> refunded."""
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="store_orders")
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="orders")
    items = models.JSONField(default=list)                             # [{"id", "title", "price", "qty", "image", "wholesale"}]
    subtotal = models.PositiveIntegerField()
    delivery = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField()
    fee = models.PositiveIntegerField(default=0)                       # XpertCreation's share of online orders
    payment = models.CharField(max_length=6, default="cod")            # cod | online
    group = models.CharField(max_length=16, blank=True, default="", db_index=True)   # one cart checkout = one group (one payment)
    status = models.CharField(max_length=12, default="placed", db_index=True)
    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=60)
    note = models.CharField(max_length=300, blank=True, default="")
    courier = models.CharField(max_length=40, blank=True, default="")
    tracking = models.CharField(max_length=60, blank=True, default="")
    provider = models.CharField(max_length=20, blank=True, default="")
    provider_ref = models.CharField(max_length=120, blank=True, default="", db_index=True)
    problem = models.CharField(max_length=300, blank=True, default="")
    rating = models.PositiveSmallIntegerField(default=0)
    review = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]


class Quote(models.Model):
    """B2B: a business asks a merchant for a price on a quantity."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="quotes")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="store_quotes")
    qty = models.PositiveIntegerField()
    message = models.CharField(max_length=1000, blank=True, default="")
    company = models.CharField(max_length=120, blank=True, default="")
    phone = models.CharField(max_length=20)
    reply_price = models.PositiveIntegerField(default=0)               # per unit
    reply = models.CharField(max_length=1000, blank=True, default="")
    status = models.CharField(max_length=8, default="open")            # open | answered | closed
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class StockMove(models.Model):
    """Inventory ledger for one product: purchases in, sales out, returns, adjustments. Stock = sum of qty."""
    KINDS = [("purchase", "Purchase"), ("sale", "Sale"), ("return", "Return / cancel"), ("adjust", "Adjustment"), ("opening", "Opening stock")]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="moves")
    kind = models.CharField(max_length=8, choices=KINDS)
    qty = models.IntegerField()                                        # + in, - out
    unit = models.PositiveIntegerField(default=0)                      # unit cost (purchase/opening) or unit sale price (sale)
    party = models.CharField(max_length=120, blank=True, default="")   # supplier or customer
    note = models.CharField(max_length=200, blank=True, default="")
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-id"]


class Review(models.Model):
    """A buyer's stars and words for one product, after the order is completed (one per product per order)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reviews")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    rating = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=800, blank=True, default="")
    reply = models.CharField(max_length=500, blank=True, default="")          # the shop's answer
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        unique_together = [("order", "product")]
