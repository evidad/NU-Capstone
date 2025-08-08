# training/fit_utils.py
from fitparse import FitFile
from datetime import datetime, timezone

KM_PER_MILE = 1.609344
M_PER_MILE = 1609.344

def parse_fit(file_obj):
    """
    Returns: date, distance_miles, duration_minutes, avg_heart_rate, avg_pace_min_per_mile
    """
    try:
        file_obj.seek(0)
    except Exception:
        pass

    fit = FitFile(file_obj)

    total_dist_m = 0.0
    total_time_s = 0.0
    avg_hr = None
    start_date = None

    for msg in fit.get_messages("session"):
        vals = {d.name: d.value for d in msg}
        if vals.get("total_distance") is not None:
            total_dist_m = float(vals["total_distance"] or 0.0)
        if vals.get("total_elapsed_time") is not None:
            total_time_s = float(vals["total_elapsed_time"] or 0.0)
        if vals.get("avg_heart_rate") is not None:
            try:
                avg_hr = int(vals["avg_heart_rate"])
            except Exception:
                pass
        if not start_date and vals.get("start_time"):
            st = vals["start_time"]
            if isinstance(st, datetime):
                start_date = st.astimezone(timezone.utc).date() if st.tzinfo else st.date()

    if avg_hr is None:
        hr_sum = 0
        hr_count = 0
        for rec in fit.get_messages("record"):
            vals = {d.name: d.value for d in rec}
            hr = vals.get("heart_rate")
            if hr is not None:
                hr_sum += int(hr); hr_count += 1
        if hr_count:
            avg_hr = int(round(hr_sum / hr_count))

    distance_miles = total_dist_m / M_PER_MILE if total_dist_m else 0.0
    duration_minutes = total_time_s / 60.0 if total_time_s else 0.0

    avg_pace_min_per_mile = None
    if distance_miles and duration_minutes:
        avg_pace_min_per_mile = round(duration_minutes / distance_miles, 2)

    return {
        "date": start_date,
        "distance_miles": round(distance_miles, 3),
        "duration_minutes": round(duration_minutes, 2),
        "avg_heart_rate": avg_hr,
        "avg_pace_min_per_mile": avg_pace_min_per_mile,
    }
