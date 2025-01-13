from typing import Optional

import requests
from ask_sdk_model.services import ServiceException
from ask_sdk_model.ui import AskForPermissionsConsentCard
from aws_lambda_powertools import Logger
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


def get_coordinates_from_address(address_parts: dict) -> Optional[tuple[float, float]]:
    try:
        address_components = []
        if address_parts.get("addressLine1"):
            address_components.append(address_parts["addressLine1"])
        if address_parts.get("city"):
            address_components.append(address_parts["city"])
        if address_parts.get("stateOrRegion"):
            address_components.append(address_parts["stateOrRegion"])
        if address_parts.get("postalCode"):
            address_components.append(address_parts["postalCode"])
        if address_parts.get("countryCode"):
            address_components.append(address_parts["countryCode"])

        if not address_components:
            return None

        query = ", ".join(address_components)
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json"
        headers = {"User-Agent": "AlexaAdhanSkill/1.0"}

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            results = response.json()
            if results:
                location = results[0]
                return float(location["lat"]), float(location["lon"])
        return None
    except Exception as e:
        logger.error(
            "Error converting address to coordinates",
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        return None


def get_device_location(
    req_envelope, response_builder, service_client_factory=None
) -> tuple:
    locale = req_envelope.request.locale
    texts = get_speech_text(locale)

    # Check if device supports geolocation
    supports_geolocation = (
        hasattr(req_envelope.context.system.device.supported_interfaces, "geolocation")
        and req_envelope.context.system.device.supported_interfaces.geolocation
        is not None
    )

    logger.info(
        "Checking device capabilities",
        extra={
            "supports_geolocation": supports_geolocation,
        },
    )

    if supports_geolocation:
        # Mobile device flow
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
                .set_card(
                    AskForPermissionsConsentCard(
                        permissions=["alexa::devices:all:geolocation:read"]
                    )
                )
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
                            geolocation and geolocation.coordinate
                            if geolocation
                            else False
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
    else:
        # Stationary device flow - use Device Settings API
        if not service_client_factory:
            logger.warning("Service client factory not provided for stationary device")
            return (False, response_builder.speak(texts.LOCATION_FAILURE).response)

        # Check for API access token
        api_access_token = req_envelope.context.system.api_access_token
        if not api_access_token:
            logger.warning("No API access token available")
            return (
                False,
                response_builder.speak(texts.NOTIFY_MISSING_PERMISSIONS)
                .set_card(
                    AskForPermissionsConsentCard(
                        permissions=["alexa::devices:all:address:full:read"]
                    )
                )
                .response,
            )

        try:
            device_id = req_envelope.context.system.device.device_id
            device_addr_client = service_client_factory.get_device_address_service()

            try:
                addr = device_addr_client.get_full_address(device_id)
                address_parts = {
                    "addressLine1": addr.addressLine1,
                    "city": addr.city,
                    "stateOrRegion": addr.stateOrRegion,
                    "postalCode": addr.postalCode,
                    "countryCode": addr.countryCode,
                }
            except ServiceException:
                addr_response = device_addr_client.get_country_and_postal_code(
                    device_id
                )
                address_parts = {
                    "postalCode": addr_response.body["postal_code"],
                    "countryCode": addr_response.body["country_code"],
                }

            logger.info(
                "Retrieved address from Device Settings API",
                extra={"address_parts": address_parts},
            )

            coordinates = get_coordinates_from_address(address_parts)
            if coordinates:
                latitude, longitude = coordinates
                logger.info(
                    "Successfully converted address to coordinates",
                    extra={"latitude": latitude, "longitude": longitude},
                )
                return (True, coordinates)

            logger.warning("Failed to convert address to coordinates")
            return (False, response_builder.speak(texts.LOCATION_FAILURE).response)

        except ServiceException as se:
            logger.error(
                "ServiceException in Device Settings API",
                extra={
                    "error_type": type(se).__name__,
                    "error_message": str(se),
                    "status_code": getattr(se, "status_code", None),
                },
            )
            if se.status_code == 403:
                return (
                    False,
                    response_builder.speak(texts.NOTIFY_MISSING_PERMISSIONS)
                    .set_card(
                        AskForPermissionsConsentCard(
                            permissions=["alexa::devices:all:address:full:read"]
                        )
                    )
                    .response,
                )
            return (False, response_builder.speak(texts.LOCATION_FAILURE).response)
        except Exception as e:
            logger.error(
                "Unexpected error in Device Settings API",
                extra={"error_type": type(e).__name__, "error_message": str(e)},
            )
            return (False, response_builder.speak(texts.LOCATION_FAILURE).response)
