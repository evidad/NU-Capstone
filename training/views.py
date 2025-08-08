# training/views.py
import os
from datetime import datetime, date as date_cls
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .fit_utils import parse_fit

class FitUploadView(APIView):
    permission_classes = [permissions.AllowAny]  # keep open for now

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
        if not f.name.lower().endswith(".fit"):
            return Response({"detail": "Only .fit files are allowed"}, status=status.HTTP_400_BAD_REQUEST)

        # Save file first
        subdir = os.path.join("uploads", "fit", datetime.now().strftime("%Y/%m/%d"))
        storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, subdir))
        filename = storage.save(f.name, f)
        file_url = settings.MEDIA_URL + f"{subdir}/{filename}"

        # IMPORTANT: Reopen the saved file (best for TemporaryUploadedFile / large files)
        saved_path = os.path.join(settings.MEDIA_ROOT, subdir, filename)
        try:
            with open(saved_path, "rb") as saved_file:
                metrics = parse_fit(saved_file)
        except Exception as e:
            # If parsing fails, return file_url anyway with an error note
            return Response(
                {"file_url": file_url, "parse_error": str(e)},
                status=status.HTTP_201_CREATED
            )

        # Fallback: if no date in file, use today's date
        if not metrics.get("date"):
            metrics["date"] = date_cls.today()

        return Response(
            {
                "file_url": file_url,
                "date": str(metrics["date"]),
                "distance_miles": metrics["distance_miles"],
                "duration_minutes": metrics["duration_minutes"],
                "avg_heart_rate": metrics["avg_heart_rate"],
                "avg_pace_min_per_mile": metrics["avg_pace_min_per_mile"],
            },
            status=status.HTTP_201_CREATED
        )
