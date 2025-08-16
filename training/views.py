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

# Django imports
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
# from django.http import HttpResponse
from django.http import JsonResponse

# Local imports
from .fit_utils import parse_fit
from .models import Workout, StravaToken
from .serializers import WorkoutSerializer
from .forms import FitUploadForm

# External library
import requests


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


# ---------- Workouts (API Upload + List + Detail) ----------
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
        rel_path = f"{subdir}/{filename}".replace("\\", "/")

        # Absolute, clickable URL
        file_url = request.build_absolute_uri(
            posixpath.join(settings.MEDIA_URL.rstrip("/"), rel_path)
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
            file_path=rel_path,
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


# ---------- Dashboard (Web upload + list) ----------
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

            # Save file
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


# ---------- Workout detail with AI insights ----------
class WorkoutPageView(LoginRequiredMixin, View):
    def get(self, request, id):
        from .services import get_workout_insights   # lazy import avoids circular issues
        workout = get_object_or_404(Workout, id=id, user=request.user)
        file_url = workout.file_path
        insights = get_workout_insights(workout)

        return render(request, "training/workout_detail.html", {
            "workout": workout,
            "file_url": file_url,
            "insights": insights,
        })


# ---------- Delete workout ----------
class WorkoutDeleteView(LoginRequiredMixin, View):
    def post(self, request, id):
        workout = get_object_or_404(Workout, id=id, user=request.user)
        workout.delete()
        messages.success(request, "Workout deleted successfully!")
        return redirect("web-dashboard")


# ---------- Strava OAuth ----------
def strava_login(request):
    redirect_uri = "http://127.0.0.1:8000/strava/callback/"
    auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={settings.STRAVA_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=read,activity:read"
    )
    return redirect(auth_url)


def strava_callback(request):
    code = request.GET.get("code")

    if not code:
        return JsonResponse({"error": "Missing code"}, status=400)

    # Step 1: Exchange code for token
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": settings.STRAVA_CLIENT_ID,
        "client_secret": settings.STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }

    res = requests.post(token_url, data=payload)
    data = res.json()

    if "access_token" not in data:
        return JsonResponse({"error": "Failed to retrieve access token", "response": data}, status=400)

    # Step 2: Save tokens to DB
    user = User.objects.first()  # Replace later with request.user if you add login
    StravaToken.objects.update_or_create(
        user=user,
        defaults={
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": datetime.fromtimestamp(data["expires_at"]),
        },
    )

    # Step 3: Fetch first 3 activities
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    activities_res = requests.get(activities_url, headers=headers, params={"per_page": 3})
    activities = activities_res.json()

    # Step 4: Redirect to dashboard and pass activities
    request.session["strava_activities"] = activities  # store in session for next view
    return redirect("dashboard")  # Make sure you have a dashboard URL/view defined


def dashboard(request):
    activities = request.session.pop("strava_activities", [])
    return render(request, "dashboard.html", {"activities": activities})

def refresh_strava_token(user):
    token = user.strava_token
    if datetime.now().timestamp() > token.expires_at.timestamp():
        url = "https://www.strava.com/oauth/token"
        payload = {
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token
        }
        res = requests.post(url, data=payload).json()
        token.access_token = res["access_token"]
        token.refresh_token = res["refresh_token"]
        token.expires_at = datetime.fromtimestamp(res["expires_at"])
        token.save()
    return token.access_token

def get_strava_activities(user):
    access_token = refresh_strava_token(user)
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    return res.json()

