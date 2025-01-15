import os
import requests
import time
import datetime
import pytz
from typing import List, Optional, Tuple
from aws_lambda_powertools import Logger
from ask_sdk_model.services import ServiceException
from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective,
    AudioItem,
    Stream,
    PlayBehavior,
)
from speech_text import get_speech_text
from ask_sdk_model.services.reminder_management import (
    Trigger,
    TriggerType,
    Recurrence,
    RecurrenceFreq,
    ReminderRequest,
    AlertInfo,
    SpokenInfo,
    SpokenText,
    PushNotification,
    PushNotificationStatus,
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
        locale: str = "en-US",
    ) -> Tuple[List[dict], str]:
        reminders = []
        formatted_times = []
        texts = get_speech_text(locale)

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

                if reminder_time < now:
                    reminder_time = user_timezone.localize(
                        datetime.datetime.combine(
                            today + datetime.timedelta(days=1), prayer_time
                        )
                    )

                formatted_times.append(
                    f"{prayer} at {prayer_time.strftime('%I:%M %p')}"
                )

                notification_time = reminder_time.strftime("%Y-%m-%dT%H:%M:%S")

                trigger = Trigger(
                    object_type=TriggerType.SCHEDULED_ABSOLUTE,
                    scheduled_time=notification_time,
                    time_zone_id=str(user_timezone),
                    recurrence=Recurrence(freq=RecurrenceFreq.DAILY, interval=1),
                )

                reminder_text = texts.PRAYER_TIME_REMINDER.format(prayer)
                text = SpokenText(locale=locale, text=reminder_text)
                alert_info = AlertInfo(SpokenInfo([text]))
                push_notification = PushNotification(PushNotificationStatus.ENABLED)

                reminder_request = ReminderRequest(
                    request_time=datetime.datetime.now(pytz.UTC).isoformat(),
                    trigger=trigger,
                    alert_info=alert_info,
                    push_notification=push_notification,
                )

                try:
                    reminder = reminder_service.create_reminder(reminder_request)
                    reminders.append(reminder)
                    logger.info(f"Successfully created reminder for {prayer}")
                except ServiceException as e:
                    if e.status_code == 401:
                        logger.error(
                            f"Unauthorized: Missing permissions for creating reminders for {prayer}",
                            extra={"error": str(e), "status_code": e.status_code},
                        )
                        raise
                    elif e.status_code == 403:  # Max reminders limit reached
                        logger.error(
                            f"Forbidden: Max reminders limit reached for {prayer}",
                            extra={"error": str(e), "status_code": e.status_code},
                        )
                        raise
                    else:
                        logger.error(
                            f"Failed to create reminder for {prayer}",
                            extra={
                                "error": str(e),
                                "status_code": getattr(e, "status_code", None),
                            },
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
