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

# add these imports near the top of training/views.py
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from .forms import FitUploadForm


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
    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WorkoutSerializer

    def get_queryset(self):
        return Workout.objects.filter(user=self.request.user).order_by("-date", "-created_at")


class WorkoutDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WorkoutSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Workout.objects.filter(user=self.request.user)

# training/views.py

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        form = FitUploadForm()
        workouts = Workout.objects.filter(user=request.user).order_by("-date", "-created_at")
        return render(request, "training/dashboard.html", {"form": form, "workouts": workouts})

    def post(self, request):
        form = FitUploadForm(request.POST, request.FILES)
        workouts = Workout.objects.filter(user=request.user).order_by("-date", "-created_at")

        if form.is_valid():
            f = form.cleaned_data["file"]
            if not f.name.lower().endswith(".fit"):
                messages.error(request, "Only .fit files are allowed.")
                return render(request, "training/dashboard.html", {"form": form, "workouts": workouts})

            # Save file to media/uploads/fit/YYYY/MM/DD/
            subdir = os.path.join("uploads", "fit", datetime.now().strftime("%Y/%m/%d"))
            storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, subdir))
            filename = storage.save(f.name, f)

            rel_path = f"{subdir}/{filename}".replace("\\", "/")

            saved_path = os.path.join(settings.MEDIA_ROOT, rel_path)
            with open(saved_path, "rb") as saved_file:
                metrics = parse_fit(saved_file)

            if not metrics.get("date"):
                metrics["date"] = date_cls.today()

            Workout.objects.create(
                user=request.user,
                date=metrics["date"],
                distance_miles=metrics["distance_miles"],
                duration_minutes=metrics["duration_minutes"],
                avg_heart_rate=metrics["avg_heart_rate"],
                avg_pace_min_per_mile=metrics["avg_pace_min_per_mile"],
                file_path=rel_path,
            )
            messages.success(request, "Workout uploaded successfully!")
            return redirect("web-dashboard")

        return render(request, "training/dashboard.html", {"form": form, "workouts": workouts})


class WorkoutPageView(LoginRequiredMixin, View):
    def get(self, request, id):
        workout = get_object_or_404(Workout, id=id, user=request.user)
        return render(request, "training/workout_detail.html", {"workout": workout})


class WorkoutDeleteView(LoginRequiredMixin, View):
    def post(self, request, id):
        workout = get_object_or_404(Workout, id=id, user=request.user)
        workout.delete()
        messages.success(request, "Workout deleted successfully!")
        return redirect("web-dashboard")
