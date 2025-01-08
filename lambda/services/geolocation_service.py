from typing import Optional

import requests
from ask_sdk_model.services import ServiceException
from ask_sdk_model.ui import AskForPermissionsConsentCard
from aws_lambda_powertools import Logger
from auth.auth_permissions import permissions
from speech_text.en_speech_text import SpeechText

logger = Logger()


def get_city_name(lat: float, lon: float) -> Optional[str]:
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {"User-Agent": "AlexaAdhanSkill/1.0"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("address", {}).get("city") or data.get("address", {}).get(
                "town"
            )
        return None
    except Exception:
        return None


def get_device_location(req_envelope, response_builder) -> dict:
    if not (
        req_envelope.context.system.user.permissions
        and req_envelope.context.system.user.permissions.consent_token
    ):
        return (
            response_builder.speak(SpeechText.NOTIFY_MISSING_PERMISSIONS)
            .set_card(AskForPermissionsConsentCard(permissions=permissions))
            .response
        )

    try:
        geolocation = req_envelope.context.geolocation
        if not geolocation or not geolocation.coordinate:
            return response_builder.speak(SpeechText.NO_LOCATION).response

        latitude = geolocation.coordinate.latitude_in_degrees
        longitude = geolocation.coordinate.longitude_in_degrees

        logger.info(
            f"Coordinates retrieved - Latitude: {latitude}, Longitude: {longitude}"
        )

        return latitude, longitude

    except ServiceException:
        return response_builder.speak(SpeechText.LOCATION_FAILURE).response
