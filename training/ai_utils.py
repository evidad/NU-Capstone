from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decouple import config
from openai import OpenAI
from .models import Workout

client = OpenAI(api_key=config("OPENAI_API_KEY"))

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
def generate_insights(workout):
    """
    Generate AI insights for a given Workout object.
    Returns a string with coaching feedback.
    """
    workout_data = (
        f"Distance: {workout.distance_miles} miles\n"
        f"Duration: {workout.duration_minutes:.1f} minutes\n"
        f"Avg HR: {workout.avg_heart_rate or 'N/A'}\n"
        f"Avg Pace: {workout.avg_pace_min_per_mile or 'N/A'} min/mile"
    )

    prompt = f"""
You are a running coach. Provide 4–5 actionable insights for this workout, 
focusing on pacing, heart rate, endurance, and recovery.

Workout details:
{workout_data}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert running coach."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"(Error generating insights: {str(e)})"