import os
import requests
import datetime
import pytz
from typing import List
from ask_sdk_model.services.reminder_management import (
    Reminder,
    TriggerAbsolute,
    AlertInfo,
    SpokenInfo,
    PushNotification,
)
from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective,
    AudioItem,
    Stream,
    PlayBehavior,
)


class PrayerService:
    BASE_URL = "http://api.aladhan.com/v1/timings"
    PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

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
        formatted = []

        for prayer in PrayerService.PRAYERS:
            if prayer in timings:
                formatted.append(f"{prayer}: {timings[prayer]}")

        return ", ".join(formatted)

    @staticmethod
    def setup_prayer_reminders(
        prayer_times: dict,
        reminder_service,
        user_timezone: pytz.timezone,
    ) -> List[Reminder]:
        reminders = []

        for prayer in PrayerService.PRAYERS:
            if prayer in prayer_times:
                prayer_time = datetime.datetime.strptime(
                    prayer_times[prayer], "%H:%M"
                ).time()

                reminder_time = datetime.datetime.combine(
                    datetime.datetime.now(user_timezone).date(), prayer_time
                )
                if reminder_time < datetime.datetime.now(user_timezone):
                    reminder_time += datetime.timedelta(days=1)

                reminder_request = Reminder(
                    trigger=TriggerAbsolute(
                        scheduled_time=reminder_time.isoformat(),
                        recurrence={"freq": "DAILY"},
                    ),
                    alert_info=AlertInfo(
                        spoken_info=SpokenInfo(content=[f"Time for {prayer} prayer"])
                    ),
                    push_notification=PushNotification(status="ENABLED"),
                )
                reminder_service.create_reminder(reminder_request)
                reminders.append(reminder_request)

        return reminders

    @staticmethod
    def get_adhan_directive() -> PlayDirective:
        adhan_url = f"{os.getenv('ATHAN_BUCKET_URL')}/adhan.mp3"

        return PlayDirective(
            play_behavior=PlayBehavior.REPLACE_ALL,
            audio_item=AudioItem(
                stream=Stream(
                    token="adhan_token",
                    url=adhan_url,
                    offset_in_milliseconds=0,
                )
            ),
        )
