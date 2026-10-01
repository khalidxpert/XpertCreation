from django.conf import settings
from django.db import models
from django.utils import timezone


class Company(models.Model):
    """A company page at /company/<slug>. KYC (documents + WhatsApp) is checked by moderators before the
    Verified badge; the website can also be verified with a file, like business cards."""
    DRAFT, PENDING, APPROVED, REJECTED = "draft", "pending", "approved", "rejected"
    STATES = [(DRAFT, "Draft"), (PENDING, "Waiting for review"), (APPROVED, "Verified"), (REJECTED, "Not approved")]
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="companies")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=60, unique=True)
    tagline = models.CharField(max_length=160, blank=True, default="")
    about = models.TextField(max_length=4000, blank=True, default="")
    industry = models.CharField(max_length=80, blank=True, default="")
    size = models.CharField(max_length=20, blank=True, default="")
    founded = models.PositiveSmallIntegerField(null=True, blank=True)
    city = models.CharField(max_length=80, blank=True, default="")
    country = models.CharField(max_length=2, blank=True, default="PK")
    address = models.CharField(max_length=240, blank=True, default="")
    website = models.URLField(max_length=200, blank=True, default="")
    email = models.EmailField(blank=True, default="")             # public
    phone = models.CharField(max_length=24, blank=True, default="")  # public
    whatsapp = models.CharField(max_length=24, blank=True, default="")  # private: for KYC contact
    logo = models.CharField(max_length=200, blank=True, default="")
    cover = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATES, default=DRAFT, db_index=True)
    review_note = models.CharField(max_length=500, blank=True, default="")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    domain = models.CharField(max_length=120, blank=True, default="")
    domain_token = models.CharField(max_length=40, blank=True, default="")
    domain_verified_at = models.DateTimeField(null=True, blank=True)
    hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class CompanyDoc(models.Model):
    """KYC proof, stored outside the website folder; only the owner and moderators can open it."""
    KINDS = [("registration", "Registration certificate"), ("cheque", "Cheque copy"), ("ntn", "NTN / tax certificate"), ("other", "Other proof")]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="docs")
    kind = models.CharField(max_length=14, choices=KINDS)
    path = models.CharField(max_length=200)
    name = models.CharField(max_length=120)
    size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(default=timezone.now)


class PersonKyc(models.Model):
    """A member's request for the blue tick: WhatsApp + ID proof + address proof, reviewed by moderators.
    Approval switches on the profile's 'verified' (the same field the admin uses)."""
    DRAFT, PENDING, APPROVED, REJECTED = "draft", "pending", "approved", "rejected"
    STATES = [(DRAFT, "Draft"), (PENDING, "Waiting for review"), (APPROVED, "Blue tick given"), (REJECTED, "Not approved")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="person_kyc")
    whatsapp = models.CharField(max_length=24, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATES, default=DRAFT, db_index=True)
    review_note = models.CharField(max_length=500, blank=True, default="")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class PersonDoc(models.Model):
    KINDS = [("cnic_front", "CNIC front"), ("cnic_back", "CNIC back"), ("passport", "Passport"), ("address", "Address proof"), ("other", "Other proof")]
    kyc = models.ForeignKey(PersonKyc, on_delete=models.CASCADE, related_name="docs")
    kind = models.CharField(max_length=12, choices=KINDS)
    path = models.CharField(max_length=200)
    name = models.CharField(max_length=120)
    size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(default=timezone.now)
