import boto3
import requests
from typing import Optional
from aws_lambda_powertools import Logger
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_model.interfaces.connections import SendRequestDirective
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model.ui import SimpleCard
from services.prayer_service import PrayerService

logger = Logger()

sb = SkillBuilder()


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speech_text = (
            "Welcome to Prayer Times. You can ask me to set up prayer notifications."
        )

        return (
            handler_input.response_builder.speak(speech_text)
            .set_card(SimpleCard("Prayer Times", speech_text))
            .set_should_end_session(False)
            .response
        )


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


class GetPrayerTimesIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetPrayerTimesIntent")(handler_input)

    def handle(self, handler_input):
        try:
            system = handler_input.request_envelope.context.system
            logger.info(f"System context: {system}")

            geo_supported = hasattr(system.device.supported_interfaces, "geolocation")
            logger.info(f"Geolocation supported: {geo_supported}")

            if not geo_supported:
                logger.warning("Device doesn't support geolocation")
                return (
                    handler_input.response_builder.speak(
                        "This device doesn't support location features."
                    )
                    .set_should_end_session(True)
                    .response
                )

            permissions = system.user.permissions
            logger.info(f"User permissions: {permissions}")

            if permissions and permissions.scopes:
                logger.info(f"Permission scopes: {permissions.scopes}")
                permission_status = permissions.scopes.get(
                    "alexa::devices:all:geolocation:read", {}
                ).get("status")
                logger.info(f"Geolocation permission status: {permission_status}")
                permission_granted = permission_status == "GRANTED"
            else:
                logger.warning("No permissions found in request")
                permission_granted = False

            logger.info(f"Permission granted: {permission_granted}")

            if not permission_granted:
                logger.info("Requesting geolocation permission")
                directive = SendRequestDirective(
                    name="AskFor",
                    payload={
                        "@type": "AskForPermissionsConsentRequest",
                        "@version": "1",
                        "permissionScope": "alexa::devices:all:geolocation:read",
                    },
                )

                return (
                    handler_input.response_builder.speak(
                        "Prayer Times needs your location. Please enable location sharing in your Alexa app."
                    )
                    .add_directive(directive)
                    .set_should_end_session(True)
                    .response
                )

            geolocation = handler_input.request_envelope.context.geolocation
            logger.info(f"Geolocation data: {geolocation}")

            if not geolocation or not geolocation.coordinate:
                logger.warning("No geolocation coordinates found")
                return (
                    handler_input.response_builder.speak(
                        "I couldn't get your location. Please try again."
                    )
                    .set_should_end_session(True)
                    .response
                )

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
                handler_input.response_builder.speak(speech_text)
                .set_card(SimpleCard("Prayer Times", speech_text))
                .set_should_end_session(True)
                .response
            )

        except Exception as e:
            logger.exception(f"Error in GetPrayerTimesIntentHandler: {e}")
            return (
                handler_input.response_builder.speak(
                    "Sorry, I couldn't fetch the prayer times at the moment."
                )
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
                handler_input.response_builder.speak(
                    "I still need location access to provide prayer times. Please enable it in the Alexa app."
                )
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
        speech_text = "You can ask me for prayer times or set up prayer notifications. What would you like to do?"

        return (
            handler_input.response_builder.speak(speech_text)
            .set_card(SimpleCard("Help", speech_text))
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
        speech_text = "I'm not sure what you want to do. You can ask me for prayer times or set up notifications."

        return (
            handler_input.response_builder.speak(speech_text)
            .set_card(SimpleCard("I didn't understand", speech_text))
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


sb.add_request_handler(ConnectionsResponseHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SetMuezzinIntentHandler())
sb.add_request_handler(GetPrayerTimesIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelAndStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(EnableNotificationsIntentHandler())


def lambda_handler(event, context):
    return sb.lambda_handler()(event, context)
