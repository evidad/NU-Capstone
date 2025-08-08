from django.urls import path
from .views import FitUploadView

urlpatterns = [
    path('upload/fit/', FitUploadView.as_view(), name='upload-fit'),
]
