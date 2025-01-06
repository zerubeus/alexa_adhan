import boto3
import requests
from typing import Optional
from aws_lambda_powertools import Logger
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model.ui import SimpleCard, AskForPermissionsConsentCard
from ask_sdk_model.services import ServiceException
from services.prayer_service import PrayerService


logger = Logger()

permissions = ["alexa::devices:all:geolocation:read"]

WELCOME = (
    "Welcome to Prayer Times. "
    "You can ask me for prayer times or set up prayer notifications. "
    "What would you like to do?"
)

WHAT_DO_YOU_WANT = "What would you like to do?"

NOTIFY_MISSING_PERMISSIONS = (
    "Prayer Times needs your location. "
    "Please enable Location permissions in the Amazon Alexa app."
)

NO_LOCATION = (
    "I couldn't get your location. "
    "Please make sure location services are enabled in the Alexa app."
)

ERROR = "Sorry, I couldn't fetch the prayer times at the moment."

LOCATION_FAILURE = (
    "There was an error accessing your location. "
    "Please try again or check your location settings in the Alexa app."
)

HELP_TEXT = (
    "You can ask me for prayer times or set up prayer notifications. "
    "For example, try saying: what are the prayer times?"
)


FALL_BACK_TEXT = "I'm not sure what you want to do. You can ask me for prayer times or set up notifications."


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

            if not (
                req_envelope.context.system.user.permissions
                and req_envelope.context.system.user.permissions.consent_token
            ):
                return (
                    response_builder.speak(NOTIFY_MISSING_PERMISSIONS)
                    .set_card(AskForPermissionsConsentCard(permissions=permissions))
                    .response
                )

            try:
                geolocation = req_envelope.context.geolocation
                if not geolocation or not geolocation.coordinate:
                    return response_builder.speak(NO_LOCATION).response

                latitude = geolocation.coordinate.latitude_in_degrees
                longitude = geolocation.coordinate.longitude_in_degrees

                logger.info(
                    f"Coordinates retrieved - Latitude: {latitude}, Longitude: {longitude}"
                )

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

            except ServiceException:
                return response_builder.speak(LOCATION_FAILURE).response

        except Exception as e:
            logger.exception(f"Error in GetPrayerTimesIntentHandler: {e}")
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


class SetMuezzinIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("SetMuezzinIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        muezzin = slots["muezzin"].value

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table("PreferencesTable")

        user_id = handler_input.request_envelope.session.user.user_id

        table.put_item(Item={"userId": user_id, "muezzin": muezzin})

        speech_text = f"I've set your athan voice to {muezzin}"

        return (
            handler_input.response_builder.speak(speech_text)
            .set_card(SimpleCard("Muezzin Set", speech_text))
            .set_should_end_session(True)
            .response
        )


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


class EnableNotificationsIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("EnableNotificationsIntent")(handler_input)

    def handle(self, handler_input):
        speech_text = "Prayer notifications feature is coming soon!"

        return (
            handler_input.response_builder.speak(speech_text)
            .set_card(SimpleCard("Notifications", speech_text))
            .set_should_end_session(True)
            .response
        )
