import datetime
import os
import time

import pytz
import requests
from ask_sdk_model.interfaces.audioplayer import (
    AudioItem,
    PlayBehavior,
    PlayDirective,
    Stream,
)
from aws_lambda_powertools import Logger
from services.geolocation_service import get_city_name, get_device_location
from speech_text import get_speech_text

logger = Logger(service="prayer_times_service")


class PrayerService:
    BASE_URL = "http://api.aladhan.com/v1/timings"
    PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    @staticmethod
    def get_prayer_times(
        latitude: float, longitude: float, method: int = 2
    ) -> dict | None:
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
                .set_should_end_session(False)
                .response
            )

        success, location_result = get_device_location(
            req_envelope, response_builder, handler_input.service_client_factory
        )

        if not success:
            return location_result

        latitude, longitude = location_result

        try:
            prayer_times = PrayerService.get_prayer_times(latitude, longitude)
            formatted_times = PrayerService.format_prayer_times(prayer_times)

            city_name = get_city_name(latitude, longitude)
            location_text = texts.LOCATION_TEXT.format(city_name) if city_name else ""
            speech_text = texts.PRIER_TIMES.format(formatted_times) + location_text

            return (
                response_builder.speak(speech_text)
                .set_should_end_session(True)
                .response
            )
        except Exception as e:
            logger.error(
                "Error getting prayer times",
                extra={"error_type": type(e).__name__, "error_message": str(e)},
            )
            return (
                response_builder.speak(texts.ERROR)
                .set_should_end_session(False)
                .response
            )

    @staticmethod
    def get_next_prayer(
        prayer_times: dict, user_timezone
    ) -> tuple[str, datetime.datetime] | None:
        """Find the next prayer based on current time.

        Args:
            prayer_times: Dictionary containing prayer times in HH:MM format
            user_timezone: The user's timezone (pytz timezone object)

        Returns:
            Tuple of (prayer_name, prayer_datetime) or None if no prayer found
        """
        now = datetime.datetime.now(user_timezone)
        today = now.date()

        for prayer in PrayerService.PRAYERS:
            if prayer in prayer_times:
                # Extract just the time part (HH:MM) from potentially longer strings
                time_str = prayer_times[prayer].split()[0]
                prayer_time = datetime.datetime.strptime(time_str, "%H:%M").time()
                prayer_datetime = user_timezone.localize(
                    datetime.datetime.combine(today, prayer_time)
                )
                if prayer_datetime > now:
                    return (prayer, prayer_datetime)

        # After Isha: next prayer is Fajr tomorrow
        if "Fajr" in prayer_times:
            time_str = prayer_times["Fajr"].split()[0]
            fajr_time = datetime.datetime.strptime(time_str, "%H:%M").time()
            tomorrow = today + datetime.timedelta(days=1)
            return (
                "Fajr",
                user_timezone.localize(datetime.datetime.combine(tomorrow, fajr_time)),
            )

        return None

    @staticmethod
    def format_time_remaining(hours: int, minutes: int, locale: str) -> str:
        """Format hours and minutes naturally with singular/plural handling.

        Args:
            hours: Number of hours remaining
            minutes: Number of minutes remaining
            locale: The user's locale (e.g., 'en-US', 'fr-FR')

        Returns:
            Formatted time string (e.g., "2 hours and 15 minutes")
        """
        is_french = locale.startswith("fr")

        if is_french:
            parts = []
            if hours > 0:
                parts.append(f"{hours} heure{'s' if hours > 1 else ''}")
            if minutes > 0:
                parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
            if not parts:
                return "moins d'une minute"
            return " et ".join(parts)
        else:
            parts = []
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
            if minutes > 0:
                parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
            if not parts:
                return "less than a minute"
            return " and ".join(parts)

    @staticmethod
    def get_next_prayer_with_location(handler_input):
        """Get next prayer countdown with location information.

        Args:
            handler_input: The Alexa handler input

        Returns:
            Response: Response containing next prayer and time remaining
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
                .set_should_end_session(False)
                .response
            )

        from services.geolocation_service import get_device_location

        success, location_result = get_device_location(
            req_envelope, response_builder, handler_input.service_client_factory
        )

        if not success:
            return location_result

        latitude, longitude = location_result

        try:
            prayer_times = PrayerService.get_prayer_times(latitude, longitude)

            # Get user's timezone from device settings
            device_id = req_envelope.context.system.device.device_id
            ups_service = handler_input.service_client_factory.get_ups_service()
            timezone_str = ups_service.get_system_time_zone(device_id)
            user_timezone = pytz.timezone(timezone_str)

            next_prayer = PrayerService.get_next_prayer(prayer_times, user_timezone)

            if next_prayer is None:
                return (
                    response_builder.speak(texts.ERROR)
                    .set_should_end_session(True)
                    .response
                )

            prayer_name, prayer_datetime = next_prayer
            now = datetime.datetime.now(user_timezone)
            time_diff = prayer_datetime - now
            total_minutes = int(time_diff.total_seconds() / 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60

            time_remaining = PrayerService.format_time_remaining(hours, minutes, locale)

            if total_minutes < 1:
                speech_text = texts.NEXT_PRAYER_LESS_THAN_MINUTE.format(prayer_name)
            else:
                speech_text = texts.NEXT_PRAYER_TIME.format(prayer_name, time_remaining)

            return (
                response_builder.speak(speech_text)
                .set_should_end_session(True)
                .response
            )
        except Exception as e:
            logger.error(
                "Error getting next prayer time",
                extra={"error_type": type(e).__name__, "error_message": str(e)},
            )
            return (
                response_builder.speak(texts.ERROR)
                .set_should_end_session(False)
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

        logger.info(
            "Handling service exception",
            extra={"exception": exception},
        )

        if exception.status_code == 403:
            return (
                handler_input.response_builder.speak(
                    texts.NOTIFY_MISSING_LOCATION_PERMISSIONS
                )
                .set_should_end_session(False)
                .response
            )

        return (
            handler_input.response_builder.speak(texts.LOCATION_FAILURE)
            .set_should_end_session(False)
            .response
        )
