from typing import Optional

import requests
from ask_sdk_model.services import ServiceException
from ask_sdk_model.ui import AskForPermissionsConsentCard
from aws_lambda_powertools import Logger
from auth.auth_permissions import permissions
from speech_text import get_speech_text

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


def get_device_location(req_envelope, response_builder) -> tuple:
    locale = req_envelope.request.locale
    texts = get_speech_text(locale)

    # Log permission state
    has_permissions = bool(req_envelope.context.system.user.permissions)
    has_consent = bool(
        req_envelope.context.system.user.permissions
        and req_envelope.context.system.user.permissions.consent_token
    )

    logger.info(
        "Checking location permissions",
        extra={
            "has_permissions": has_permissions,
            "has_consent_token": has_consent,
        },
    )

    if not (has_permissions and has_consent):
        logger.warning(
            "Missing location permissions or consent token",
            extra={
                "has_permissions": has_permissions,
                "has_consent_token": has_consent,
            },
        )
        return (
            False,
            response_builder.speak(texts.NOTIFY_MISSING_PERMISSIONS)
            .set_card(AskForPermissionsConsentCard(permissions=permissions))
            .response,
        )

    try:
        geolocation = req_envelope.context.geolocation
        logger.info(
            "Geolocation object state",
            extra={
                "has_geolocation": bool(geolocation),
                "has_coordinate": bool(
                    geolocation and geolocation.coordinate if geolocation else False
                ),
                "raw_geolocation": str(geolocation) if geolocation else None,
            },
        )

        if not geolocation or not geolocation.coordinate:
            logger.warning(
                "No geolocation data available",
                extra={
                    "has_geolocation": bool(geolocation),
                    "has_coordinate": bool(
                        geolocation and geolocation.coordinate if geolocation else False
                    ),
                },
            )
            return (False, response_builder.speak(texts.NO_LOCATION).response)

        latitude = geolocation.coordinate.latitude_in_degrees
        longitude = geolocation.coordinate.longitude_in_degrees

        logger.info(
            "Successfully retrieved coordinates",
            extra={"latitude": latitude, "longitude": longitude},
        )

        return (True, (latitude, longitude))

    except ServiceException as se:
        logger.error(
            "ServiceException in get_device_location",
            extra={
                "error_type": type(se).__name__,
                "error_message": str(se),
                "status_code": getattr(se, "status_code", None),
            },
        )
        return (False, response_builder.speak(texts.LOCATION_FAILURE).response)
    except Exception as e:
        logger.error(
            "Unexpected error in get_device_location",
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        return (False, response_builder.speak(texts.LOCATION_FAILURE).response)
