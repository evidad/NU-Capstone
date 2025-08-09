import os
import posixpath
from datetime import datetime, date as date_cls

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .fit_utils import parse_fit
from .models import Workout
from .serializers import WorkoutSerializer


class FitUploadView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
        if not f.name.lower().endswith(".fit"):
            return Response({"detail": "Only .fit files are allowed"}, status=status.HTTP_400_BAD_REQUEST)

        # Save to media/uploads/fit/YYYY/MM/DD/
        subdir = os.path.join("uploads", "fit", datetime.now().strftime("%Y/%m/%d"))
        storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, subdir))
        filename = storage.save(f.name, f)

        # Windows-safe: normalize to URL-style path
        rel_path = f"{subdir}/{filename}"                 # may contain backslashes
        rel_path_url = rel_path.replace("\\", "/")         # force forward slashes for URLs

        # Absolute, clickable URL
        file_url = request.build_absolute_uri(
            posixpath.join(settings.MEDIA_URL.rstrip("/"), rel_path_url)
        )

        # Parse metrics
        saved_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        with open(saved_path, "rb") as saved_file:
            metrics = parse_fit(saved_file)

        if not metrics.get("date"):
            metrics["date"] = date_cls.today()

        # Persist (store normalized URL-style path)
        w = Workout.objects.create(
            date=metrics["date"],
            distance_miles=metrics["distance_miles"],
            duration_minutes=metrics["duration_minutes"],
            avg_heart_rate=metrics["avg_heart_rate"],
            avg_pace_min_per_mile=metrics["avg_pace_min_per_mile"],
            file_path=rel_path_url,  # <- normalized!
        )

        # Serialize with absolute URL
        data = WorkoutSerializer(w, context={"request": request}).data
        data["file_url"] = file_url
        return Response(data, status=status.HTTP_201_CREATED)



class WorkoutListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = WorkoutSerializer
    def get_queryset(self):
        return Workout.objects.all().order_by("-date", "-created_at")
    
class WorkoutDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]  # TODO: lock down later
    serializer_class = WorkoutSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Workout.objects.all()


