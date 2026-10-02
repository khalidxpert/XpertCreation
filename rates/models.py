from django.db import models


class Rate(models.Model):
    """Today's value for one item (PKR). Currencies are fetched; gold and fuel are entered by staff."""
    key = models.CharField(max_length=16, unique=True)
    value = models.DecimalField(max_digits=14, decimal_places=2)
    source = models.CharField(max_length=60, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)


class RateDay(models.Model):
    """One value per item per day, for the 30-day charts."""
    key = models.CharField(max_length=16, db_index=True)
    day = models.DateField(db_index=True)
    value = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        unique_together = [("key", "day")]
