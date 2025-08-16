# training/urls_web.py
from django.urls import path
from .views import DashboardView, WorkoutPageView, WorkoutDeleteView

urlpatterns = [
    path("", DashboardView.as_view(), name="web-dashboard"),
    path("workout/<uuid:id>/", WorkoutPageView.as_view(), name="web-workout-detail"),
    path("workout/<uuid:id>/delete/", WorkoutDeleteView.as_view(), name="web-workout-delete"),
]
