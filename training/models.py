import uuid
from django.db import models
from django.contrib.auth import get_user_model 
from django.contrib.auth.models import User

User = get_user_model()

class Workout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workouts")
    date = models.DateField() 
    distance_miles = models.FloatField()
    duration_minutes = models.FloatField()
    avg_heart_rate = models.IntegerField(null=True, blank=True)
    avg_pace_min_per_mile = models.FloatField(null=True, blank=True)
    file_path = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.user.username} – {self.date} – {self.distance_miles:.2f} mi"
    
class StravaToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="strava_token")
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    athlete_id = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"StravaToken for athlete {self.athlete_id}"
