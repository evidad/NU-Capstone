import os
import posixpath
from datetime import datetime, date as date_cls

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib.auth import get_user_model

from rest_framework import status, permissions, generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .fit_utils import parse_fit
from .models import Workout
from .serializers import WorkoutSerializer

User = get_user_model()


# ---------- Auth: Register ----------
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        user = User(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


# ---------- Workouts ----------
class FitUploadView(APIView):
    permission_classes = [IsAuthenticated]

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

        # Normalize for URL
        rel_path = f"{subdir}/{filename}"              # may contain backslashes on Windows
        rel_path_url = rel_path.replace("\\", "/")      # force forward slashes

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

        # Persist (attach to current user)
        w = Workout.objects.create(
            user=request.user,
            date=metrics["date"],
            distance_miles=metrics["distance_miles"],
            duration_minutes=metrics["duration_minutes"],
            avg_heart_rate=metrics["avg_heart_rate"],
            avg_pace_min_per_mile=metrics["avg_pace_min_per_mile"],
            file_path=rel_path_url,
        )

        data = WorkoutSerializer(w, context={"request": request}).data
        data["file_url"] = file_url
        return Response(data, status=status.HTTP_201_CREATED)


class WorkoutListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkoutSerializer

    def get_queryset(self):
        return Workout.objects.filter(user=self.request.user).order_by("-date", "-created_at")


class WorkoutDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkoutSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Workout.objects.filter(user=self.request.user)
