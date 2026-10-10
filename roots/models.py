"""Roots of Love: family trees (shajra). A family has people (alive or late) linked by father, mother and spouse.
Members with an account join by code or invite link and can claim the profile that is theirs.
Inside a family: tree, relations, phone directory, album, notice board, birthdays and barsi reminders."""
from django.conf import settings
from django.db import models


class Family(models.Model):
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=10, unique=True)             # join code, e.g. RL7K2QX9
    clan = models.CharField(max_length=60, blank=True)              # tribe / clan (optional)
    city = models.CharField(max_length=60, blank=True)
    country = models.CharField(max_length=40, blank=True, default="Pakistan")
    about = models.TextField(max_length=1000, blank=True)
    join_open = models.BooleanField(default=True)                   # the join code works
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="roots_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Person(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="people")
    name = models.CharField(max_length=80)
    gender = models.CharField(max_length=1, choices=[("m", "Male"), ("f", "Female")])
    father = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    mother = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    spouse = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    alive = models.BooleanField(default=True)
    born = models.DateField(null=True, blank=True)
    died = models.DateField(null=True, blank=True)
    married = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=60, blank=True)
    work = models.CharField(max_length=80, blank=True)
    notes = models.TextField(max_length=600, blank=True)
    photo = models.CharField(max_length=120, blank=True)            # path under MEDIA_ROOT
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="roots_people")
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Membership(models.Model):
    ADMIN, MEMBER, PENDING = "admin", "member", "pending"
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="roots_memberships")
    role = models.CharField(max_length=8, default=MEMBER)
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")   # "this is me"
    note = models.CharField(max_length=200, blank=True)             # join request: "I am Ahmed's son"
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("family", "user")]


class Invite(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="invites")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    token = models.CharField(max_length=24, unique=True)
    by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    used_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    expires = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class Notice(models.Model):
    KINDS = [("news", "News"), ("event", "Event"), ("reminder", "Reminder"), ("dua", "Dua request"), ("sad", "Sad news")]
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="notices")
    by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    kind = models.CharField(max_length=10, default="news")
    text = models.TextField(max_length=1500)
    day = models.DateField(null=True, blank=True)                   # event / reminder date
    told = models.BooleanField(default=False)                       # day-before reminder sent
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class Photo(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="photos")
    by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    path = models.CharField(max_length=120)
    caption = models.CharField(max_length=200, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
