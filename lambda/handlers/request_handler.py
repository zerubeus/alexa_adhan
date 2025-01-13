import pytz
import requests
from aws_lambda_powertools import Logger
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler,
    AbstractExceptionHandler,
)
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model.services import ServiceException
from ask_sdk_model.ui import AskForPermissionsConsentCard, SimpleCard
from services.prayer_times_service import PrayerService
from services.geolocation_service import get_device_location, get_city_name
from auth.auth_permissions import permissions
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

            # Check if we have the permissions
            if not (
                req_envelope.context.system.user.permissions
                and req_envelope.context.system.user.permissions.consent_token
            ):
                logger.warning("Missing permissions for device address")
                return (
                    response_builder.speak(texts.NOTIFY_MISSING_PERMISSIONS)
                    .set_card(
                        AskForPermissionsConsentCard(
                            permissions=["alexa::devices:all:address:full:read"]
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
            location_text = f" in {city_name}" if city_name else ""

            speech_text = (
                f"Here are today's prayer times{location_text}: {formatted_times}"
            )

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
                            permissions=["alexa::devices:all:address:full:read"]
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

            req_envelope = handler_input.request_envelope
            response_builder = handler_input.response_builder

            # First, ask for location permission if not granted
            if not (
                req_envelope.context.system.user.permissions
                and req_envelope.context.system.user.permissions.consent_token
            ):
                logger.warning("Missing location permissions")
                return (
                    response_builder.speak(
                        "To get prayer times, I need access to your location. I've sent a card to help you enable this permission."
                    )
                    .set_card(
                        AskForPermissionsConsentCard(
                            permissions=["alexa::devices:all:address:full:read"]
                        )
                    )
                    .response
                )

            # Get location first
            success, location_result = get_device_location(
                req_envelope, response_builder, handler_input.service_client_factory
            )

            if not success:
                return location_result

            latitude, longitude = location_result

            # Get prayer times
            try:
                prayer_times = PrayerService.get_prayer_times(latitude, longitude)
                if not prayer_times:
                    logger.error("Failed to get prayer times after retries")
                    return response_builder.speak(texts.ERROR).response

                # Ask for reminder permission via voice
                if "alexa::alerts:reminders:skill:readwrite" not in (
                    req_envelope.context.system.user.permissions.scopes or {}
                ):
                    logger.info("Requesting reminder permissions via voice")
                    from ask_sdk_model.interfaces.connections import (
                        SendRequestDirective,
                    )

                    return (
                        response_builder.speak(texts.ASK_REMINDER_PERMISSION)
                        .add_directive(
                            SendRequestDirective(
                                name="AskFor",
                                payload={
                                    "@type": "AskForPermissionsConsentRequest",
                                    "@version": "1",
                                    "permissionScope": "alexa::alerts:reminders:skill:readwrite",
                                },
                                token="user_reminder_permission",
                            )
                        )
                        .response
                    )

                # If we have both permissions, proceed with reminder setup
                device_id = req_envelope.context.system.device.device_id
                timezone = handler_input.service_client_factory.get_ups_service().get_system_time_zone(
                    device_id
                )
                user_timezone = pytz.timezone(timezone)

                reminder_service = (
                    handler_input.service_client_factory.get_reminder_management_service()
                )

                reminders, formatted_times = PrayerService.setup_prayer_reminders(
                    prayer_times,
                    reminder_service,
                    user_timezone,
                )

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

            except ServiceException as se:
                if se.status_code == 403:  # Max reminders limit reached
                    return response_builder.speak(texts.MAX_REMINDERS_ERROR).response
                raise  # Let the outer exception handler deal with other service exceptions
            except requests.exceptions.RequestException as e:
                logger.error(
                    "Failed to fetch prayer times",
                    extra={
                        "error": str(e),
                        "status_code": (
                            getattr(e.response, "status_code", None)
                            if hasattr(e, "response")
                            else None
                        ),
                    },
                )
                return response_builder.speak(texts.ERROR).response

        except ServiceException as se:
            logger.error(
                "ServiceException in EnableNotificationsIntentHandler",
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
                            permissions=["alexa::devices:all:address:full:read"]
                        )
                    )
                    .response
                )
            return response_builder.speak(texts.LOCATION_FAILURE).response

        except Exception as e:
            logger.exception(f"Error in EnableNotificationsIntentHandler: {e}")
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


class ConnectionsResponseHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("Connections.Response")(handler_input)

    def handle(self, handler_input):
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)
        request = handler_input.request_envelope.request

        if request.name == "AskFor" and request.status.code == "200":
            if request.payload.get("status") == "ACCEPTED":
                # Permission granted, proceed with reminder setup
                try:
                    req_envelope = handler_input.request_envelope
                    response_builder = handler_input.response_builder

                    success, location_result = get_device_location(
                        req_envelope,
                        response_builder,
                        handler_input.service_client_factory,
                    )

                    if not success:
                        return location_result

                    latitude, longitude = location_result

                    prayer_times = PrayerService.get_prayer_times(latitude, longitude)
                    if not prayer_times:
                        logger.error("Failed to get prayer times after retries")
                        return response_builder.speak(texts.ERROR).response

                    device_id = req_envelope.context.system.device.device_id
                    timezone = handler_input.service_client_factory.get_ups_service().get_system_time_zone(
                        device_id
                    )
                    user_timezone = pytz.timezone(timezone)

                    reminder_service = (
                        handler_input.service_client_factory.get_reminder_management_service()
                    )

                    reminders, formatted_times = PrayerService.setup_prayer_reminders(
                        prayer_times,
                        reminder_service,
                        user_timezone,
                    )

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

                except ServiceException as se:
                    if se.status_code == 403:  # Max reminders limit reached
                        return response_builder.speak(
                            texts.MAX_REMINDERS_ERROR
                        ).response
                    logger.error(
                        "ServiceException in ConnectionsResponseHandler",
                        extra={
                            "error_type": type(se).__name__,
                            "error_message": str(se),
                            "status_code": getattr(se, "status_code", None),
                        },
                    )
                    return response_builder.speak(texts.ERROR).response
                except Exception as e:
                    logger.exception(f"Error in ConnectionsResponseHandler: {e}")
                    return handler_input.response_builder.speak(texts.ERROR).response
            else:
                # Permission denied
                return (
                    handler_input.response_builder.speak(texts.PERMISSION_DENIED)
                    .set_should_end_session(True)
                    .response
                )

        return handler_input.response_builder.speak(texts.ERROR).response
