from django.conf import settings
from openai import OpenAI

# Initialize client with your API key
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_workout_insights(workout):
    """
    Send workout data to OpenAI and return recommendations.
    """
    prompt = f"""
    You are a running coach. Analyze this workout and provide 2-3
    actionable coaching tips.

    Date: {workout.date}
    Distance: {workout.distance_miles:.2f} miles
    Duration: {workout.duration_minutes:.2f} minutes
    Avg HR: {workout.avg_heart_rate if workout.avg_heart_rate else "N/A"}
    Pace: {workout.avg_pace_min_per_mile if workout.avg_pace_min_per_mile else "N/A"} min/mile
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # or gpt-4o, gpt-3.5-turbo, etc.
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )

    return response.choices[0].message.content
