import uuid6
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid6.uuid7,
        editable=False,
        help_text="Unique ID in UUID v7.",
    )
    name = models.CharField(max_length=255, db_index=True, unique=True)
    gender = models.CharField(max_length=50, db_index=True)
    gender_probability = models.FloatField(db_index=True)
    age = models.IntegerField(db_index=True)
    age_group = models.CharField(max_length=50, db_index=True)
    country_id = models.CharField(max_length=2, db_index=True)
    country_name = models.CharField(max_length=255)
    country_probability = models.FloatField(db_index=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id})"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["country_id", "age_group"]),
            models.Index(fields=["gender", "age"]),
        ]
