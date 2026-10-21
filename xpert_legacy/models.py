import uuid

from django.conf import settings
from django.db import models


class LegalDocumentRequest(models.Model):
    """Audit trail — which document was generated, by whom, and when."""

    DOC_TYPES = [
        ("rent-agreement", "Rent Agreement"),
        ("affidavit", "Affidavit"),
        ("sale-agreement", "Sale Agreement"),
        ("power-of-attorney", "Power of Attorney"),
        ("society-ndc", "No Demand Certificate"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    doc_type = models.CharField(max_length=40, choices=DOC_TYPES)
    payload = models.JSONField(default=dict)
    reference_no = models.CharField(max_length=24, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def save(self, *args, **kwargs):
        if not self.reference_no:
            self.reference_no = "XD-" + uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.get_doc_type_display()} · {self.reference_no}"
