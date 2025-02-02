import pytz
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler,
    AbstractExceptionHandler,
)
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model.interfaces.connections import SendRequestDirective
from ask_sdk_model.services import ServiceException
from ask_sdk_model.ui import AskForPermissionsConsentCard, SimpleCard
from aws_lambda_powertools import Logger

from auth.auth_permissions import permissions
from services.geolocation_service import get_device_location, get_city_name
from services.prayer_times_service import PrayerService
from speech_text import get_speech_text

logger = Logger()


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)

        return (
            handler_input.response_builder.speak(texts.WELCOME)
            .ask(texts.WHAT_DO_YOU_WANT)
            .set_card(SimpleCard("Prayer Times", texts.WELCOME))
            .set_should_end_session(False)
            .response
        )


class GetPrayerTimesIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetPrayerTimesIntent")(handler_input)

    def handle(self, handler_input):
        try:
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

        except ServiceException as se:
            logger.error(
                "ServiceException in GetPrayerTimesIntentHandler",
                extra={
                    "error_type": type(se).__name__,
                    "error_message": str(se),
                    "status_code": getattr(se, "status_code", None),
                },
            )
            if se.status_code == 403:
                return (
                    response_builder.speak(texts.NOTIFY_MISSING_PERMISSIONS)
                    .set_card(
                        AskForPermissionsConsentCard(
                            permissions=permissions["full_address_r"]
                        )
                    )
                    .response
                )
            return response_builder.speak(texts.LOCATION_FAILURE).response

        except Exception as e:
            logger.exception(f"Error in GetPrayerTimesIntentHandler: {e}")
            return handler_input.response_builder.speak(texts.ERROR).response


class EnableNotificationsIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("EnableNotificationsIntent")(handler_input)

    def handle(self, handler_input):
        try:
            locale = handler_input.request_envelope.request.locale
            texts = get_speech_text(locale)

            # Check for reminder permissions
            alexa_permissions = (
                handler_input.request_envelope.context.system.user.permissions
            )
            has_reminder_permission = (
                alexa_permissions
                and hasattr(alexa_permissions, "scopes")
                and alexa_permissions.scopes
                and permissions["reminder_rw"] in alexa_permissions.scopes
            )

            if not has_reminder_permission:
                logger.info(
                    "Reminder permissions not found in scopes, requesting permissions",
                    extra={
                        "has_permissions": bool(alexa_permissions),
                        "has_scopes": (
                            hasattr(alexa_permissions, "scopes")
                            if alexa_permissions
                            else False
                        ),
                        "scopes": (
                            alexa_permissions.scopes
                            if (
                                alexa_permissions
                                and hasattr(alexa_permissions, "scopes")
                            )
                            else None
                        ),
                        "reminder_permission": permissions["reminder_rw"],
                    },
                )
                try:
                    return (
                        handler_input.response_builder.speak(
                            texts.ASK_REMINDER_PERMISSION
                        )
                        .add_directive(
                            SendRequestDirective(
                                name="AskFor",
                                payload={
                                    "@type": "AskForPermissionsConsentRequest",
                                    "@version": "2",
                                    "permissionScopes": [
                                        {
                                            "permissionScope": permissions[
                                                "reminder_rw"
                                            ],
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
                        handler_input.response_builder.speak(
                            texts.NOTIFY_MISSING_PERMISSIONS
                        )
                        .set_card(
                            AskForPermissionsConsentCard(
                                permissions=permissions["reminder_rw"]
                            )
                        )
                        .response
                    )

            # If we have permissions, proceed with setup
            logger.info("Reminder permissions found in scopes, proceeding with setup")
            return self._setup_reminders(handler_input)

        except Exception as e:
            logger.exception(
                "Error in EnableNotificationsIntentHandler",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "traceback": True,
                },
            )
            return handler_input.response_builder.speak(texts.ERROR).response

    def _setup_reminders(self, handler_input):
        try:
            locale = handler_input.request_envelope.request.locale
            texts = get_speech_text(locale)
            req_envelope = handler_input.request_envelope
            response_builder = handler_input.response_builder

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

            prayer_times = PrayerService.get_prayer_times(latitude, longitude)
            if not prayer_times:
                logger.error("Failed to get prayer times after retries")
                return response_builder.speak(texts.ERROR).response

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
                "Error in _setup_reminders",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "traceback": True,
                },
            )
            return handler_input.response_builder.speak(texts.ERROR).response


class ConnectionsResponseHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("Connections.Response")(handler_input)

    def handle(self, handler_input):
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
                    req_envelope = handler_input.request_envelope
                    response_builder = handler_input.response_builder

                    alexa_permissions = req_envelope.context.system.user.permissions

                    logger.info(
                        f"ConnectionsResponseHandler Permissions: {alexa_permissions}"
                    )

                    if not (alexa_permissions and alexa_permissions.consent_token):
                        logger.error(
                            "Missing reminder permissions after user accepted",
                            extra={
                                "permissions": str(alexa_permissions),
                                "has_token": bool(alexa_permissions.consent_token),
                            },
                        )

                        return (
                            response_builder.speak(texts.NOTIFY_MISSING_PERMISSIONS)
                            .set_card(
                                AskForPermissionsConsentCard(
                                    permissions=[permissions["reminder_rw"]]
                                )
                            )
                            .response
                        )

                    alexa_permissions = req_envelope.context.system.user.permissions

                    if not (alexa_permissions and alexa_permissions.consent_token):
                        logger.error(
                            "Missing location permissions",
                            extra={
                                "permissions": str(alexa_permissions),
                                "has_token": (
                                    bool(alexa_permissions.consent_token)
                                    if alexa_permissions
                                    else False
                                ),
                            },
                        )
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

                    prayer_times = PrayerService.get_prayer_times(latitude, longitude)
                    if not prayer_times:
                        logger.error("Failed to get prayer times after retries")
                        return response_builder.speak(texts.ERROR).response

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

                    try:
                        reminder_service = (
                            handler_input.service_client_factory.get_reminder_management_service()
                        )

                        logger.info("Setting up prayer reminders")

                        reminders, formatted_times = (
                            PrayerService.setup_prayer_reminders(
                                prayer_times,
                                reminder_service,
                                user_timezone,
                                locale=locale,
                            )
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
                            return response_builder.speak(
                                texts.MAX_REMINDERS_ERROR
                            ).response
                        return response_builder.speak(texts.ERROR).response

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


class GetPrayerTimesExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return isinstance(exception, ServiceException)

    def handle(self, handler_input, exception):
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


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)

        logger.exception(f"Unexpected error: {exception}")
        return (
            handler_input.response_builder.speak(texts.ERROR).ask(texts.ERROR).response
        )


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)

        return (
            handler_input.response_builder.speak(texts.HELP_TEXT)
            .set_card(SimpleCard("Help", texts.HELP_TEXT))
            .set_should_end_session(False)
            .response
        )


class CancelAndStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.CancelIntent")(handler_input) or is_intent_name(
            "AMAZON.StopIntent"
        )(handler_input)

    def handle(self, handler_input):
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)

        return (
            handler_input.response_builder.speak(texts.GOODBYE)
            .set_card(SimpleCard("Goodbye", texts.GOODBYE))
            .set_should_end_session(True)
            .response
        )


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)

        return (
            handler_input.response_builder.speak(texts.FALL_BACK_TEXT)
            .set_card(SimpleCard("I didn't understand", texts.FALL_BACK_TEXT))
            .set_should_end_session(False)
            .response
        )
