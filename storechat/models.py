"""Store chat: a buyer chats with a shop. The shop's auto-replies (its own questions and answers, plus built-in
answers from the product details) reply at once; anything else waits for the seller, who gets a bell."""
from django.conf import settings
from django.db import models


class Bot(models.Model):
    merchant = models.OneToOneField("store.Merchant", on_delete=models.CASCADE, related_name="chatbot")
    on = models.BooleanField(default=True)                                  # auto-replies on / off
    greeting = models.CharField(max_length=300, blank=True, default="")
    away = models.CharField(max_length=300, blank=True, default="")         # when the seller is not online


class Faq(models.Model):
    merchant = models.ForeignKey("store.Merchant", on_delete=models.CASCADE, related_name="chatfaqs")
    q = models.CharField(max_length=160)
    keys = models.CharField(max_length=300, blank=True, default="")         # comma separated words that trigger it
    a = models.TextField(max_length=1000)
    on = models.BooleanField(default=True)
    pos = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["pos", "id"]


class Thread(models.Model):
    merchant = models.ForeignKey("store.Merchant", on_delete=models.CASCADE, related_name="chats")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shopchats")
    product = models.ForeignKey("store.Product", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    last = models.CharField(max_length=200, blank=True, default="")
    buyer_unread = models.PositiveIntegerField(default=0)
    seller_unread = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = [("merchant", "buyer")]
        ordering = ["-updated_at"]


class Msg(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="msgs")
    who = models.CharField(max_length=6)                                    # buyer | seller | bot
    text = models.TextField(max_length=1000)
    product_id = models.PositiveIntegerField(null=True, blank=True)
    open = models.BooleanField(default=False)                               # buyer question no auto-reply answered
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["id"]
