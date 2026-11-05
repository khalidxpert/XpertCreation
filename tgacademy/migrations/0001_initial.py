import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("academy", "__first__")]
    operations = [
        migrations.CreateModel(name="TgLink", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("tg_id", models.BigIntegerField(unique=True)),
            ("tg_username", models.CharField(blank=True, default="", max_length=64)),
            ("created", models.DateTimeField(default=django.utils.timezone.now)),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="tg_link", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="LoginTicket", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("token_hash", models.CharField(max_length=64, unique=True)),
            ("next_url", models.CharField(default="/academy/", max_length=200)),
            ("expires", models.DateTimeField()),
            ("used", models.DateTimeField(blank=True, null=True)),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tg_tickets", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="Enrollment", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("source", models.CharField(default="telegram", max_length=20)),
            ("order_id", models.CharField(max_length=40, unique=True)),
            ("created", models.DateTimeField(default=django.utils.timezone.now)),
            ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tg_enrollments", to="academy.course")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tg_enrollments", to=settings.AUTH_USER_MODEL)),
        ], options={"unique_together": {("user", "course")}}),
    ]
