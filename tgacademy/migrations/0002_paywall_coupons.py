import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tgacademy", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("academy", "__first__")]
    operations = [
        migrations.CreateModel(name="Paywall", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("on", models.BooleanField(default=True)),
            ("started", models.DateTimeField(default=django.utils.timezone.now)),
            ("updated", models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(name="Coupon", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("code", models.CharField(max_length=24, unique=True)),
            ("max_uses", models.PositiveIntegerField(default=1)),
            ("uses", models.PositiveIntegerField(default=0)),
            ("expires", models.DateTimeField(blank=True, null=True)),
            ("active", models.BooleanField(default=True)),
            ("note", models.CharField(blank=True, default="", max_length=120)),
            ("created", models.DateTimeField(default=django.utils.timezone.now)),
            ("course", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="coupons", to="academy.course")),
            ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ("for_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="CouponUse", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created", models.DateTimeField(default=django.utils.timezone.now)),
            ("coupon", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="used_by", to="tgacademy.coupon")),
            ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="academy.course")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="academy_coupons", to=settings.AUTH_USER_MODEL)),
        ], options={"unique_together": {("user", "course")}}),
        migrations.CreateModel(name="CouponRequest", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("message", models.CharField(blank=True, default="", max_length=400)),
            ("status", models.CharField(db_index=True, default="open", max_length=10)),
            ("created", models.DateTimeField(default=django.utils.timezone.now)),
            ("decided", models.DateTimeField(blank=True, null=True)),
            ("coupon", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="tgacademy.coupon")),
            ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="academy.course")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to=settings.AUTH_USER_MODEL)),
        ]),
    ]
