from rest_framework import serializers
from django.conf import settings
from .models import Workout

class WorkoutSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Workout
        fields = [
            "id","date","distance_miles","duration_minutes",
            "avg_heart_rate","avg_pace_min_per_mile",
            "file_path","created_at","file_url",
        ]

    def get_file_url(self, obj):
        rel = (obj.file_path or "").replace("\\", "/")
        url = settings.MEDIA_URL + rel
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("file_path"):
            data["file_path"] = data["file_path"].replace("\\", "/")
        return data
