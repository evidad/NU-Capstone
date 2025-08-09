import uuid
from django.db import models

class Workout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    distance_miles = models.FloatField()
    duration_minutes = models.FloatField()
    avg_heart_rate = models.IntegerField(null=True, blank=True)
    avg_pace_min_per_mile = models.FloatField(null=True, blank=True)
    file_path = models.CharField(max_length=512)  # store relative media path
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date} – {self.distance_miles:.2f} mi"
