from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler,
    AbstractExceptionHandler,
)
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model.services import ServiceException
from ask_sdk_model.ui import AskForPermissionsConsentCard, SimpleCard
from aws_lambda_powertools import Logger

from auth.auth_permissions import permissions
from services.geolocation_service import get_device_location, get_city_name
from services.prayer_times_service import PrayerService
from services.notification_service import NotificationService
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

            if not NotificationService.check_reminder_permission(alexa_permissions):
                return NotificationService.request_reminder_permission(
                    handler_input.response_builder, texts
                )

            # If we have permissions, proceed with setup
            logger.info("Reminder permissions found in scopes, proceeding with setup")
            return NotificationService.setup_prayer_notifications(handler_input)

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


class ConnectionsResponseHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("Connections.Response")(handler_input)

    def handle(self, handler_input):
        return NotificationService.handle_connections_response(handler_input)


class GetPrayerTimesExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return isinstance(exception, ServiceException)

    def handle(self, handler_input, exception):
        return NotificationService.handle_service_exception(handler_input, exception)


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
