from datetime import date, datetime, timedelta

import httpx


def get_week_range(year, week):
    first_day_of_year = datetime(year, 1, 1)
    first_monday = first_day_of_year + timedelta(days=(7 - first_day_of_year.weekday()) % 7)
    first_day_of_week = first_monday + timedelta(weeks=week - 1)
    last_day_of_week = first_day_of_week + timedelta(days=6)
    return first_day_of_week.strftime("%Y-%m-%d"), last_day_of_week.strftime("%Y-%m-%d")


def get_first_day_of_current_week():
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())
    return start_of_week.date().strftime("%Y-%m-%d")


def get_week_days(week_str):
    year, week = map(int, week_str.split("-"))
    start_date = date.fromisocalendar(year, week, 1)
    return [(start_date + timedelta(days=i)).isoformat() for i in range(7)]


def handle_response(response: httpx.Response):
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e}")
        content = get_content(response)
        return {"error": str(e), "content": content}

    if response.status_code == 204:
        return None

    return get_content(response)


def get_content(response: httpx.Response):
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text
