import os
import posixpath
from openai import OpenAI


from datetime import datetime, timezone as dt_timezone, date as date_cls

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

# from django.utils.timezone import now
from django.utils import timezone


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
    
from django.shortcuts import render, get_object_or_404
from .models import Workout
from openai import OpenAI
import os

def workout_detail(request, strava_id):
    workout = get_object_or_404(Workout, strava_id=strava_id)

    client = OpenAI(api_key=settings.OPENAI_API_KEY)  # initialize here

    prompt = f"""
    You are a running coach. Give me short, actionable insights on this workout:
    - Distance: {workout.distance_miles:.2f} miles
    - Duration: {workout.duration_minutes:.2f} minutes
    - Average Heart Rate: {workout.avg_heart_rate if workout.avg_heart_rate else "N/A"} bpm
    - Average Pace: {workout.avg_pace_min_per_mile if workout.avg_pace_min_per_mile else "N/A"} min/mi
    """

    insights = None
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert running coach."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
        )
        insights = response.choices[0].message.content.strip()
    except Exception as e:
        insights = f"(Error generating insights: {e})"

    return render(request, "training/workout_detail.html", {
        "workout": workout,
        "insights": insights,
    })

# def workout_delete(request, pk):
#     workout = get_object_or_404(Workout, pk=pk)
#     if request.method == "POST":
#         workout.delete()
#         return redirect("web-dashboard")  # name for dashboard view
#     return render(request, "training/confirm_delete.html", {"workout": workout})



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
        return JsonResponse(
            {"error": "Failed to retrieve access token", "response": data}, status=400
        )

    # Step 2: Save tokens to DB
    user = User.objects.first()  # TODO: replace with request.user once auth is in place
    StravaToken.objects.update_or_create(
    user=user,
    defaults={
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": datetime.fromtimestamp(data["expires_at"], tz=dt_timezone.utc),  # use stdlib utc
        "updated_at": timezone.now(),  # Django’s timezone
        },
    )

    # Step 3: Fetch activities from Strava
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    activities_res = requests.get(activities_url, headers=headers, params={"per_page": 3})
    activities = activities_res.json()

    # Step 4: Save activities to DB
    for act in activities:
        Workout.objects.update_or_create(
            strava_id=act["id"],
            user=user,
            defaults={
                "date": act.get("start_date_local", timezone.now()),
                "distance_miles": round(act.get("distance", 0) / 1609.34, 2),
                "duration_minutes": round(act.get("moving_time", 0) / 60, 2),
                "avg_heart_rate": act.get("average_heartrate"),
                "avg_pace_min_per_mile": (
                    round((act["moving_time"] / 60) / (act["distance"] / 1609.34), 2)
                    if act.get("distance") and act.get("moving_time")
                    else None
                ),
            },
        )

    # Step 5: Redirect to dashboard (data now in DB)
    return redirect("dashboard")

def save_strava_activities(user, activities):
    """
    Takes a list of Strava activity dicts and saves/updates them in the DB.
    """
    for act in activities:
        Workout.objects.update_or_create(
            strava_id=act["id"],   # unique identifier from Strava
            user=user,
            defaults={
                "date": act.get("start_date_local", timezone.now()),
                "distance_miles": round(act.get("distance", 0) / 1609.34, 2),  # meters → miles
                "duration_minutes": round(act.get("moving_time", 0) / 60, 2),  # seconds → minutes
                "avg_heart_rate": act.get("average_heartrate"),
                "avg_pace_min_per_mile": (
                    round((act["moving_time"] / 60) / (act["distance"] / 1609.34), 2)
                    if act.get("distance") and act.get("moving_time") else None
                ),
            }
        )


def dashboard(request):
    user = request.user
    activities = get_strava_activities(user, per_page=3)

    workouts = []
    for a in activities:
        distance_miles = a["distance"] / 1609.34  # meters → miles
        duration_minutes = a["moving_time"] / 60  # seconds → minutes
        avg_pace = (duration_minutes / distance_miles) if distance_miles > 0 else None

        workouts.append({
            "date": a["start_date_local"][:10],
            "distance_miles": distance_miles,
            "duration_minutes": duration_minutes,
            "avg_heart_rate": a.get("average_heartrate"),
            "avg_pace_min_per_mile": avg_pace,
            "id": a["id"],
        })

    return render(request, "training/dashboard.html", {"workouts": workouts})

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

def get_strava_activities(user, per_page=3):
    try:
        token = StravaToken.objects.get(user=user)
    except StravaToken.DoesNotExist:
        return []

    # refresh if expired
    if token.expires_at <= timezone.now():
        refresh_url = "https://www.strava.com/oauth/token"
        refresh_payload = {
            "client_id": settings.STRAVA_CLIENT_ID,
            "client_secret": settings.STRAVA_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
        }
        res = requests.post(refresh_url, data=refresh_payload)
        data = res.json()
        token.access_token = data["access_token"]
        token.refresh_token = data["refresh_token"]
        token.expires_at = datetime.fromtimestamp(data["expires_at"])
        token.save()

    headers = {"Authorization": f"Bearer {token.access_token}"}
    url = "https://www.strava.com/api/v3/athlete/activities"
    res = requests.get(url, headers=headers, params={"per_page": per_page})
    return res.json()

