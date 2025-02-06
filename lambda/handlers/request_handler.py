from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler,
    AbstractExceptionHandler,
)
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model.services import ServiceException
from ask_sdk_model.ui import AskForPermissionsConsentCard
from aws_lambda_powertools import Logger

from services.prayer_notification_service import PrayerNotificationService
from services.prayer_times_service import PrayerService
from speech_text import get_speech_text
from auth.auth_permissions import permissions

logger = Logger()


# [Prayer times intent handlers]


class GetPrayerTimesIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetPrayerTimesIntent")(handler_input)

    def handle(self, handler_input):
        return PrayerService.get_prayer_times_with_location(handler_input)


class GetPrayerTimesExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return isinstance(exception, ServiceException)

    def handle(self, handler_input, exception):
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
                .response
            )
        return handler_input.response_builder.speak(texts.LOCATION_FAILURE).response


# [Prayer notification intent handlers]


class EnableNotificationsIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("EnableNotificationsIntent")(handler_input)

    def handle(self, handler_input):
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)

        # Check for reminder permissions
        alexa_permissions = (
            handler_input.request_envelope.context.system.user.permissions
        )

        logger.info(
            "EnableNotificationsIntentHandler Alexa permissions",
            extra={"permissions": alexa_permissions},
        )

        has_reminder_permission = PrayerNotificationService.check_reminder_permission(
            alexa_permissions
        )

        if not has_reminder_permission:
            return PrayerNotificationService.request_reminder_permission(
                handler_input.response_builder, texts
            )

        # If we have permissions, proceed with setup
        logger.info("Reminder permissions found in scopes, proceeding with setup")
        return PrayerNotificationService.setup_prayer_notifications(handler_input)


class ConnectionsResponseHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("Connections.Response")(handler_input)

    def handle(self, handler_input):
        return PrayerNotificationService.handle_connections_response(handler_input)


# [General intent handlers]


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
            .set_should_end_session(False)
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
            handler_input.response_builder.speak(texts.ERROR)
            .set_should_end_session(False)
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)

        return (
            handler_input.response_builder.speak(texts.HELP_TEXT)
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
            .set_should_end_session(False)
            .response
        )
