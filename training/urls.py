from django.urls import path
from .views import FitUploadView, WorkoutListView, WorkoutDetailView

urlpatterns = [
    path('upload/fit/', FitUploadView.as_view(), name='upload-fit'),
    path('workouts/', WorkoutListView.as_view(), name='workout-list'),
    path('workouts/<uuid:id>/', WorkoutDetailView.as_view(), name='workout-detail'),
]
