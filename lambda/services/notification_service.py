import pytz
from aws_lambda_powertools import Logger
from ask_sdk_model.services import ServiceException
from ask_sdk_model.interfaces.connections import SendRequestDirective
from ask_sdk_model.ui import AskForPermissionsConsentCard

from services.geolocation_service import get_device_location
from services.prayer_times_service import PrayerService
from speech_text import get_speech_text
from auth.auth_permissions import permissions

logger = Logger()


class NotificationService:
    @staticmethod
    def get_permission_status(permissions_obj, permission_key):
        """Get the status of a specific permission."""
        if not permissions_obj or not hasattr(permissions_obj, "scopes"):
            return None

        scopes = permissions_obj.scopes
        if not isinstance(scopes, dict):
            return None

        permission_data = scopes.get(permission_key, {})
        if not isinstance(permission_data, dict):
            return None

        return permission_data.get("status")

    @staticmethod
    def check_reminder_permission(alexa_permissions):
        """Check if the user has granted reminder permissions."""
        has_reminder_permission = (
            NotificationService.get_permission_status(
                alexa_permissions, permissions["reminder_rw"]
            )
            == "GRANTED"
        )

        if not has_reminder_permission:
            logger.info(
                "Reminder permissions not found in scopes or not granted",
                extra={
                    "has_permissions": bool(alexa_permissions),
                    "has_scopes": (
                        hasattr(alexa_permissions, "scopes")
                        if alexa_permissions
                        else False
                    ),
                    "scopes": (
                        alexa_permissions.scopes
                        if (alexa_permissions and hasattr(alexa_permissions, "scopes"))
                        else None
                    ),
                    "reminder_permission": permissions["reminder_rw"],
                },
            )
            return False
        return True

    @staticmethod
    def request_reminder_permission(response_builder, texts):
        """Request reminder permission from the user."""
        try:
            return (
                response_builder.speak(texts.ASK_REMINDER_PERMISSION)
                .add_directive(
                    SendRequestDirective(
                        name="AskFor",
                        payload={
                            "@type": "AskForPermissionsConsentRequest",
                            "@version": "2",
                            "permissionScopes": [
                                {
                                    "permissionScope": permissions["reminder_rw"],
                                    "consentLevel": "ACCOUNT",
                                }
                            ],
                        },
                        token="user_reminder_permission",
                    )
                )
                .response
            )
        except ServiceException as se:
            logger.error(
                "ServiceException while requesting permissions",
                extra={
                    "error": str(se),
                    "status_code": getattr(se, "status_code", None),
                },
            )
            # Fallback to card if voice permission fails
            return (
                response_builder.speak(texts.NOTIFY_MISSING_PERMISSIONS)
                .set_card(
                    AskForPermissionsConsentCard(permissions=permissions["reminder_rw"])
                )
                .response
            )

    @staticmethod
    def setup_prayer_notifications(handler_input):
        """Set up prayer notifications for the user."""
        try:
            locale = handler_input.request_envelope.request.locale
            texts = get_speech_text(locale)
            req_envelope = handler_input.request_envelope
            response_builder = handler_input.response_builder

            # Get device location
            success, location_result = get_device_location(
                req_envelope,
                response_builder,
                handler_input.service_client_factory,
            )

            if not success:
                logger.error(
                    "Failed to get device location",
                    extra={"location_result": str(location_result)},
                )
                return location_result

            latitude, longitude = location_result
            logger.info(
                "Successfully got device location",
                extra={"latitude": latitude, "longitude": longitude},
            )

            # Get prayer times
            prayer_times = PrayerService.get_prayer_times(latitude, longitude)
            if not prayer_times:
                logger.error("Failed to get prayer times after retries")
                return response_builder.speak(texts.ERROR).response

            # Get user timezone
            device_id = req_envelope.context.system.device.device_id
            try:
                timezone = handler_input.service_client_factory.get_ups_service().get_system_time_zone(
                    device_id
                )
                user_timezone = pytz.timezone(timezone)
                logger.info("Got user timezone", extra={"timezone": timezone})
            except Exception as e:
                logger.error(
                    "Failed to get user timezone",
                    extra={
                        "error_type": type(e).__name__,
                        "error": str(e),
                        "device_id": device_id,
                    },
                )
                return response_builder.speak(texts.ERROR).response

            # Set up reminders
            try:
                reminder_service = (
                    handler_input.service_client_factory.get_reminder_management_service()
                )
                logger.info("Setting up prayer reminders")

                reminders, formatted_times = PrayerService.setup_prayer_reminders(
                    prayer_times,
                    reminder_service,
                    user_timezone,
                    locale=locale,
                )

                logger.info(
                    "Successfully set up reminders",
                    extra={
                        "num_reminders": len(reminders),
                        "formatted_times": formatted_times,
                    },
                )
            except ServiceException as e:
                logger.error(
                    "Failed to set up reminders",
                    extra={
                        "error": str(e),
                        "status_code": getattr(e, "status_code", None),
                        "error_type": type(e).__name__,
                        "traceback": True,
                    },
                )

                if e.status_code == 401:
                    return (
                        response_builder.speak(texts.NOTIFY_MISSING_PERMISSIONS)
                        .set_card(
                            AskForPermissionsConsentCard(
                                permissions=permissions["reminder_rw"]
                            )
                        )
                        .response
                    )
                elif e.status_code == 403:
                    return response_builder.speak(texts.MAX_REMINDERS_ERROR).response
                return response_builder.speak(texts.ERROR).response

            # Return success response
            confirmation_text = texts.REMINDER_SETUP_CONFIRMATION.format(
                formatted_times
            )
            play_directive = PrayerService.get_adhan_directive()

            return (
                response_builder.speak(confirmation_text)
                .add_directive(play_directive)
                .set_should_end_session(True)
                .response
            )

        except Exception as e:
            logger.exception(
                "Error in setup_prayer_notifications",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "traceback": True,
                },
            )
            return handler_input.response_builder.speak(texts.ERROR).response

    @staticmethod
    def handle_connections_response(handler_input):
        """Handle the Connections.Response for reminder permission requests."""
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)
        request = handler_input.request_envelope.request

        logger.info(
            "Handling Connections.Response",
            extra={
                "request_id": handler_input.request_envelope.request.request_id,
                "request_name": request.name,
                "status_code": request.status.code,
                "payload_status": (
                    request.payload.get("status") if request.payload else None
                ),
                "locale": locale,
            },
        )

        if request.name == "AskFor" and request.status.code == "200":
            if request.payload.get("status") == "ACCEPTED":
                try:
                    alexa_permissions = (
                        handler_input.request_envelope.context.system.user.permissions
                    )
                    logger.info(
                        f"ConnectionsResponseHandler Permissions: {alexa_permissions}"
                    )

                    if not NotificationService.check_reminder_permission(
                        alexa_permissions
                    ):
                        logger.error(
                            "Missing reminder permissions after user accepted",
                            extra={
                                "permissions": str(alexa_permissions),
                                "has_token": bool(
                                    getattr(alexa_permissions, "consent_token", None)
                                ),
                            },
                        )
                        return handler_input.response_builder.speak(
                            "Pour configurer les rappels par la voix, dites 'Activer notifications'."
                        ).response

                    return NotificationService.setup_prayer_notifications(handler_input)

                except Exception as e:
                    logger.exception(
                        "Unexpected error in ConnectionsResponseHandler",
                        extra={
                            "error_type": type(e).__name__,
                            "error": str(e),
                            "traceback": True,
                        },
                    )
                    return handler_input.response_builder.speak(texts.ERROR).response
            else:
                logger.info("User denied permission request")
                return (
                    handler_input.response_builder.speak(texts.PERMISSION_DENIED)
                    .set_should_end_session(True)
                    .response
                )

        logger.error(
            "Invalid request",
            extra={"request_name": request.name, "status_code": request.status.code},
        )
        return handler_input.response_builder.speak(texts.ERROR).response
