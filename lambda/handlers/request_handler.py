import os
from datetime import datetime, timedelta

import pytz
from ask_sdk_core.dispatch_components import (
    AbstractExceptionHandler,
    AbstractRequestHandler,
)
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_model.interfaces.audioplayer import (
    AudioItem,
    PlayBehavior,
    PlayDirective,
    Stream,
)
from ask_sdk_model.services import ServiceException
from ask_sdk_model.services.reminder_management import (
    AlertInfo,
    PushNotification,
    Reminder,
    SpokenInfo,
    TriggerAbsolute,
)
from ask_sdk_model.ui import AskForPermissionsConsentCard, SimpleCard
from aws_lambda_powertools import Logger
from auth.auth_permissions import permissions
from services.geolocation_service import get_city_name, get_device_location
from services.prayer_times_service import PrayerService
from speech_text.en_speech_text import (
    ERROR,
    FALL_BACK_TEXT,
    HELP_TEXT,
    LOCATION_FAILURE,
    NOTIFICATION_SETUP_TEXT,
    NOTIFY_MISSING_PERMISSIONS,
    WELCOME,
    WHAT_DO_YOU_WANT,
)

logger = Logger()


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):

        return (
            handler_input.response_builder.speak(WELCOME)
            .ask(WHAT_DO_YOU_WANT)
            .set_card(SimpleCard("Prayer Times", WELCOME))
            .set_should_end_session(False)
            .response
        )


class GetPrayerTimesIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetPrayerTimesIntent")(handler_input)

    def handle(self, handler_input):
        try:
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
            return handler_input.response_builder.speak(ERROR).response


class EnableNotificationsIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("EnableNotificationsIntent")(handler_input)

    def handle(self, handler_input):
        try:
            req_envelope = handler_input.request_envelope
            response_builder = handler_input.response_builder

            try:
                latitude, longitude = get_device_location(
                    req_envelope, response_builder
                )

                device_id = req_envelope.context.system.device.device_id

                timezone = handler_input.service_client_factory.ups_service.get_system_time_zone(
                    device_id
                )

                user_timezone = pytz.timezone(timezone)

                prayer_times = PrayerService.get_prayer_times(latitude, longitude)

                reminder_service = (
                    handler_input.service_client_factory.get_reminder_management_service()
                )

                prayers = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

                for prayer in prayers:
                    if prayer in prayer_times:
                        prayer_time = datetime.strptime(
                            prayer_times[prayer], "%H:%M"
                        ).time()

                        reminder_time = datetime.combine(
                            datetime.now(user_timezone).date(), prayer_time
                        )
                        if reminder_time < datetime.now(user_timezone):
                            reminder_time += timedelta(days=1)

                        reminder_request = Reminder(
                            trigger=TriggerAbsolute(
                                scheduled_time=reminder_time.isoformat(),
                                recurrence={"freq": "DAILY"},
                            ),
                            alert_info=AlertInfo(
                                spoken_info=SpokenInfo(
                                    content=[f"Time for {prayer} prayer"]
                                )
                            ),
                            push_notification=PushNotification(status="ENABLED"),
                        )
                        reminder_service.create_reminder(reminder_request)

                adhan_url = f"{os.getenv('ATHAN_BUCKET_URL')}/adhan.mp3"

                play_directive = PlayDirective(
                    play_behavior=PlayBehavior.REPLACE_ALL,
                    audio_item=AudioItem(
                        stream=Stream(
                            token="adhan_token",
                            url=adhan_url,
                            offset_in_milliseconds=0,
                        )
                    ),
                )

                return (
                    response_builder.speak(NOTIFICATION_SETUP_TEXT)
                    .add_directive(play_directive)
                    .set_should_end_session(True)
                    .response
                )

            except ServiceException:
                return response_builder.speak(LOCATION_FAILURE).response

        except Exception as e:
            logger.exception(f"Error in EnableNotificationsIntentHandler: {e}")
            return handler_input.response_builder.speak(ERROR).response


class GetPrayerTimesExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return isinstance(exception, ServiceException)

    def handle(self, handler_input, exception):
        if exception.status_code == 403:
            return (
                handler_input.response_builder.speak(NOTIFY_MISSING_PERMISSIONS)
                .set_card(AskForPermissionsConsentCard(permissions=permissions))
                .response
            )

        return (
            handler_input.response_builder.speak(LOCATION_FAILURE)
            .ask(LOCATION_FAILURE)
            .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.exception(f"Unexpected error: {exception}")
        speech = "Sorry, something went wrong. Please try again!"
        return handler_input.response_builder.speak(speech).ask(speech).response


class ConnectionsResponseHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("Connections.Response")(handler_input)

    def handle(self, handler_input):
        response = handler_input.request_envelope.request

        logger.info(f"Connections.Response received: {response}")
        logger.info(f"Response status code: {response.status.code}")

        if response.status.code == "200":
            logger.info("Permission granted, proceeding to get prayer times")
            return GetPrayerTimesIntentHandler().handle(handler_input)
        else:
            logger.warning(
                f"Permission not granted. Status code: {response.status.code}"
            )
            return (
                handler_input.response_builder.speak(NOTIFY_MISSING_PERMISSIONS)
                .set_should_end_session(True)
                .response
            )


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        return (
            handler_input.response_builder.speak(HELP_TEXT)
            .set_card(SimpleCard("Help", HELP_TEXT))
            .set_should_end_session(False)
            .response
        )


class CancelAndStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.CancelIntent")(handler_input) or is_intent_name(
            "AMAZON.StopIntent"
        )(handler_input)

    def handle(self, handler_input):
        speech_text = "Goodbye!"

        return (
            handler_input.response_builder.speak(speech_text)
            .set_card(SimpleCard("Goodbye", speech_text))
            .set_should_end_session(True)
            .response
        )


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        return (
            handler_input.response_builder.speak(FALL_BACK_TEXT)
            .set_card(SimpleCard("I didn't understand", FALL_BACK_TEXT))
            .set_should_end_session(False)
            .response
        )
