import os
import requests
import time
import datetime
import pytz
from typing import Optional
from aws_lambda_powertools import Logger
from ask_sdk_model.ui import AskForPermissionsConsentCard, SimpleCard
from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective,
    AudioItem,
    Stream,
    PlayBehavior,
)
from services.geolocation_service import get_device_location, get_city_name
from speech_text import get_speech_text
from auth.auth_permissions import permissions
from ask_sdk_model.services import ServiceException

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
                response_builder.speak(texts.NOTIFY_MISSING_LOCATION_PERMISSIONS)
                .set_card(
                    AskForPermissionsConsentCard(
                        permissions=permissions["full_address_r"]
                    )
                )
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
                .set_card(SimpleCard("Prayer Times", speech_text))
                .set_should_end_session(True)
                .response
            )
        except ServiceException as se:
            return PrayerService.handle_service_exception(handler_input, se)
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
                handler_input.response_builder.speak(
                    texts.NOTIFY_MISSING_LOCATION_PERMISSIONS
                )
                .set_card(
                    AskForPermissionsConsentCard(
                        permissions=permissions["full_address_r"]
                    )
                )
                .set_should_end_session(False)
                .response
            )

        return (
            handler_input.response_builder.speak(texts.LOCATION_FAILURE)
            .set_should_end_session(False)
            .response
        )
