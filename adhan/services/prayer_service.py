import requests
import datetime
import pytz


class PrayerService:
    BASE_URL = "http://api.aladhan.com/v1/timings"

    @staticmethod
    def get_prayer_times(latitude: float, longitude: float, method: int = 2) -> dict:
        """
        Get prayer times from Aladhan API
        method=2 is Islamic Society of North America (ISNA)
        """
        now = datetime.datetime.now(pytz.UTC)

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "method": method,
            "timestamp": int(now.timestamp()),
        }

        response = requests.get(PrayerService.BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()
        return data["data"]["timings"]

    @staticmethod
    def format_prayer_times(timings: dict) -> str:
        prayers = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
        formatted = []

        for prayer in prayers:
            if prayer in timings:
                formatted.append(f"{prayer}: {timings[prayer]}")

        return ", ".join(formatted)
