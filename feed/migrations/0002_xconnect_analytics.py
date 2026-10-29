from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("feed", "0001_initial"),
    ]

    operations = [
        migrations.AddField(model_name="post", name="reshares_count",
                            field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="post", name="impressions",
                            field=models.PositiveIntegerField(default=0)),
        migrations.CreateModel(
            name="Reshare",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reshares", to="feed.post")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-id"], "unique_together": {("post", "user")}},
        ),
        migrations.CreateModel(
            name="ImpressionDay",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day", models.DateField(db_index=True)),
                ("count", models.PositiveIntegerField(default=0)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("author", "day")}},
        ),
    ]
