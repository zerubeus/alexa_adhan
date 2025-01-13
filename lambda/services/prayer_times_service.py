import os
import requests
import time
import datetime
import pytz
from typing import List, Optional, Tuple
from aws_lambda_powertools import Logger
from ask_sdk_model.services import ServiceException
from ask_sdk_model.services.reminder_management import (
    Reminder,
    Trigger,
    AlertInfo,
    SpokenInfo,
    PushNotification,
    RecurrenceFreq,
    Recurrence,
)
from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective,
    AudioItem,
    Stream,
    PlayBehavior,
)

logger = Logger()


class PrayerService:
    BASE_URL = "http://api.aladhan.com/v1/timings"
    PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    @staticmethod
    def get_prayer_times(
        latitude: float, longitude: float, method: int = 2
    ) -> Optional[dict]:
        """
        Get prayer times from Aladhan API with retry logic
        method=2 is Islamic Society of North America (ISNA)
        """
        now = datetime.datetime.now(pytz.UTC)
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "method": method,
            "timestamp": int(now.timestamp()),
        }

        for attempt in range(PrayerService.MAX_RETRIES):
            try:
                response = requests.get(
                    PrayerService.BASE_URL,
                    params=params,
                    timeout=5,
                    headers={"User-Agent": "AlexaAdhanSkill/1.0"},
                )
                response.raise_for_status()
                data = response.json()
                return data["data"]["timings"]
            except requests.exceptions.RequestException as e:
                logger.error(
                    "Aladhan API error",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": PrayerService.MAX_RETRIES,
                        "error": str(e),
                        "status_code": (
                            getattr(e.response, "status_code", None)
                            if hasattr(e, "response")
                            else None
                        ),
                    },
                )
                if attempt < PrayerService.MAX_RETRIES - 1:
                    time.sleep(PrayerService.RETRY_DELAY)
                    continue
                raise

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
    ) -> Tuple[List[Reminder], str]:
        reminders = []
        formatted_times = []

        for prayer in PrayerService.PRAYERS:
            if prayer in prayer_times:
                prayer_time = datetime.datetime.strptime(
                    prayer_times[prayer], "%H:%M"
                ).time()

                now = datetime.datetime.now(user_timezone)
                today = now.date()

                reminder_time = user_timezone.localize(
                    datetime.datetime.combine(today, prayer_time)
                )

                # Set reminder 10 minutes before prayer time
                reminder_time = reminder_time - datetime.timedelta(minutes=10)

                if reminder_time < now:
                    reminder_time = user_timezone.localize(
                        datetime.datetime.combine(
                            today + datetime.timedelta(days=1), prayer_time
                        )
                    ) - datetime.timedelta(minutes=10)

                formatted_times.append(
                    f"{prayer} at {prayer_time.strftime('%I:%M %p')}"
                )

                trigger = Trigger(
                    type="SCHEDULED_ABSOLUTE",
                    scheduled_time=reminder_time.isoformat(),
                    recurrence=Recurrence(
                        freq=RecurrenceFreq.DAILY,
                    ),
                )

                reminder_request = Reminder(
                    request_time=datetime.datetime.now(pytz.UTC).isoformat(),
                    trigger=trigger,
                    alert_info=AlertInfo(
                        spoken_info=SpokenInfo(
                            content=[f"Time for {prayer} prayer in 10 minutes"]
                        )
                    ),
                    push_notification=PushNotification(status="ENABLED"),
                )

                try:
                    reminder = reminder_service.create_reminder(reminder_request)
                    reminders.append(reminder)
                except ServiceException as e:
                    if e.status_code == 403:  # Max reminders limit reached
                        raise
                    logger.error(
                        f"Failed to create reminder for {prayer}",
                        extra={"error": str(e), "status_code": e.status_code},
                    )

        return reminders, ", ".join(formatted_times)

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
