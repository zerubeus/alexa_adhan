import os
import requests
import time
import datetime
import pytz
from typing import List, Optional, Tuple
from aws_lambda_powertools import Logger
from ask_sdk_model.services import ServiceException
from ask_sdk_model.ui import AskForPermissionsConsentCard, SimpleCard
from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective,
    AudioItem,
    Stream,
    PlayBehavior,
)
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
from services.geolocation_service import get_device_location, get_city_name
from speech_text import get_speech_text
from auth.auth_permissions import permissions

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

        logger.info(
            "Starting to set up prayer reminders",
            extra={
                "num_prayers": len(PrayerService.PRAYERS),
                "timezone": str(user_timezone),
                "locale": locale,
                "prayer_times": prayer_times,
            },
        )

        for prayer in PrayerService.PRAYERS:
            if prayer in prayer_times:
                try:
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

                    logger.info(
                        f"Setting up reminder for {prayer}",
                        extra={
                            "prayer": prayer,
                            "notification_time": notification_time,
                            "timezone": str(user_timezone),
                            "reminder_time": str(reminder_time),
                            "current_time": str(now),
                        },
                    )

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
                        logger.info(
                            f"Creating reminder for {prayer}",
                            extra={
                                "prayer": prayer,
                                "reminder_request": str(reminder_request),
                                "trigger_time": notification_time,
                            },
                        )

                        reminder = reminder_service.create_reminder(reminder_request)
                        reminders.append(reminder)

                        logger.info(
                            f"Successfully created reminder for {prayer}",
                            extra={
                                "prayer": prayer,
                                "reminder_id": getattr(reminder, "alert_token", None),
                                "reminder_status": getattr(reminder, "status", None),
                            },
                        )
                    except ServiceException as e:
                        if e.status_code == 401:
                            logger.error(
                                f"Unauthorized: Missing permissions for creating reminder for {prayer}",
                                extra={
                                    "prayer": prayer,
                                    "error": str(e),
                                    "status_code": e.status_code,
                                    "request": str(reminder_request),
                                    "error_type": type(e).__name__,
                                },
                            )
                            raise
                        elif e.status_code == 403:  # Max reminders limit reached
                            logger.error(
                                f"Forbidden: Max reminders limit reached for {prayer}",
                                extra={
                                    "prayer": prayer,
                                    "error": str(e),
                                    "status_code": e.status_code,
                                    "request": str(reminder_request),
                                    "error_type": type(e).__name__,
                                },
                            )
                            raise
                        else:
                            logger.error(
                                f"Failed to create reminder for {prayer}",
                                extra={
                                    "prayer": prayer,
                                    "error": str(e),
                                    "status_code": getattr(e, "status_code", None),
                                    "request": str(reminder_request),
                                    "error_type": type(e).__name__,
                                    "traceback": True,
                                },
                            )
                            raise
                except Exception as e:
                    logger.error(
                        f"Error processing reminder for {prayer}",
                        extra={
                            "prayer": prayer,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "traceback": True,
                        },
                    )
                    raise

        logger.info(
            "Completed setting up reminders",
            extra={
                "num_reminders_created": len(reminders),
                "formatted_times": formatted_times,
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

    @staticmethod
    def get_prayer_times_with_location(handler_input):
        """Get prayer times with location information.

        Args:
            handler_input: The Alexa handler input

        Returns:
            Response: Response containing prayer times and location information

        Raises:
            ServiceException: If there are permission or location service issues
        """
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)
        req_envelope = handler_input.request_envelope
        response_builder = handler_input.response_builder
        alexa_permissions = req_envelope.context.system.user.permissions

        if not (alexa_permissions and alexa_permissions.consent_token):
            logger.warning("Missing permissions for device address")
            return (
                response_builder.speak(texts.NOTIFY_MISSING_PERMISSIONS)
                .set_card(
                    AskForPermissionsConsentCard(
                        permissions=permissions["full_address_r"]
                    )
                )
                .response
            )

        success, location_result = get_device_location(
            req_envelope, response_builder, handler_input.service_client_factory
        )

        if not success:
            return location_result

        latitude, longitude = location_result

        prayer_times = PrayerService.get_prayer_times(latitude, longitude)
        formatted_times = PrayerService.format_prayer_times(prayer_times)

        city_name = get_city_name(latitude, longitude)
        location_text = texts.LOCATION_TEXT.format(city_name) if city_name else ""
        speech_text = texts.PRIER_TIMES.format(formatted_times) + location_text

        return (
            response_builder.speak(speech_text)
            .set_card(SimpleCard("Prayer Times", speech_text))
            .response
        )

    @staticmethod
    def handle_service_exception(handler_input, exception):
        """Handle service exceptions and return appropriate responses.

        Args:
            handler_input: The Alexa handler input
            exception: The ServiceException that was caught

        Returns:
            Response: Appropriate response based on the exception type
        """
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)

        if exception.status_code == 403:
            return (
                handler_input.response_builder.speak(texts.NOTIFY_MISSING_PERMISSIONS)
                .set_card(AskForPermissionsConsentCard(permissions=permissions))
                .response
            )

        return (
            handler_input.response_builder.speak(texts.LOCATION_FAILURE)
            .ask(texts.LOCATION_FAILURE)
            .response
        )
