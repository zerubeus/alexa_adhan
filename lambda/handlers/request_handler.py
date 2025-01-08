import pytz
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

            latitude, longitude = get_device_location(req_envelope, response_builder)

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

            latitude, longitude = get_device_location(req_envelope, response_builder)

            device_id = req_envelope.context.system.device.device_id
            timezone = (
                handler_input.service_client_factory.ups_service.get_system_time_zone(
                    device_id
                )
            )
            user_timezone = pytz.timezone(timezone)

            prayer_times = PrayerService.get_prayer_times(latitude, longitude)
            reminder_service = (
                handler_input.service_client_factory.get_reminder_management_service()
            )

            PrayerService.setup_prayer_reminders(
                prayer_times,
                reminder_service,
                user_timezone,
            )

            play_directive = PrayerService.get_adhan_directive()

            return (
                response_builder.speak(texts.NOTIFICATION_SETUP_TEXT)
                .add_directive(play_directive)
                .set_should_end_session(True)
                .response
            )

        except ServiceException:
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