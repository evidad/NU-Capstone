AI Virtual Running Coach – MVP Backend (Manual .FIT Upload)

--- Thurs, Aug 8

Project setup

Created a clean Python virtual environment (.venv) and activated it.

Installed Django and Django REST Framework (pip install django djangorestframework).

Started a new Django project named coach_backend.

Verified the server runs successfully at http://127.0.0.1:8000/.

App creation

Created a training app for workout-related features.

Added training and rest_framework to INSTALLED_APPS in settings.py.

Configured MEDIA_URL and MEDIA_ROOT to handle uploaded files.

Upload-only API endpoint

Implemented a FitUploadView API view that:

Accepts .fit files via POST request (form-data key file).

Saves them into media/uploads/fit/YYYY/MM/DD/.

Returns the file URL in the response.

Configured urls.py in both training and coach_backend to serve this endpoint.

Tested successfully with Postman, confirming a 201 Created status.

.FIT file parsing

Installed fitparse and python-dateutil for file analysis.

Added a parse_fit() helper function to extract:

Workout date

Distance (miles)

Duration (minutes)

Average heart rate

Average pace (min/mi)

Updated the upload endpoint to return parsed metrics along with the file URL.

Verified Postman responses include accurate workout data.

Unit preference

Modified parsing logic to report values in miles and min/mi for pace instead of kilometers.

--- Fri, Aug 9

