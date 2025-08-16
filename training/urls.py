from django.urls import path
from .views import (
    FitUploadView,
    WorkoutListView,
    WorkoutDetailView,
    strava_login,
    strava_callback,
)
from . import views

urlpatterns = [
    path("upload/fit/", FitUploadView.as_view(), name="upload-fit"),
    path("workouts/", WorkoutListView.as_view(), name="workout-list"),
    path("workouts/<uuid:id>/", WorkoutDetailView.as_view(), name="workout-detail"),
    path("strava/login/", strava_login, name="strava-login"),
    path("strava/callback/", strava_callback, name="strava-callback"),
    path("api/strava/login/", views.strava_login, name="strava-login"),
    path("api/strava/callback/", views.strava_callback, name="strava-callback"),
    path("workouts/<int:strava_id>/", views.workout_detail, name="workout_detail"),
    # path("workout/<int:pk>/delete/", views.workout_delete, name="web-workout-delete"),
]
