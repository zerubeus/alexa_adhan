import boto3
import requests
from typing import Optional
from aws_lambda_powertools import Logger
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
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
            geo_supported = hasattr(system.device.supported_interfaces, "geolocation")

            if not geo_supported:
                return (
                    handler_input.response_builder.speak(
                        "This device doesn't support location features."
                    )
                    .set_should_end_session(True)
                    .response
                )

            permissions = system.user.permissions
            if permissions and permissions.scopes.get(
                "alexa::devices:all:geolocation:read"
            ):
                permission_granted = (
                    permissions.scopes["alexa::devices:all:geolocation:read"].status
                    == "GRANTED"
                )
            else:
                permission_granted = False

            if not permission_granted:
                return (
                    handler_input.response_builder.speak(
                        "Prayer Times needs your location. Please enable location sharing in your Alexa app."
                    )
                    .add_directive(
                        {
                            "type": "Connections.SendRequest",
                            "name": "AskFor",
                            "payload": {
                                "@type": "AskForPermissionsConsentRequest",
                                "@version": "1",
                                "permissionScope": "alexa::devices:all:geolocation:read",
                            },
                        }
                    )
                    .set_should_end_session(True)
                    .response
                )

            geolocation = handler_input.request_envelope.context.geolocation

            if not geolocation or not geolocation.coordinate:
                return (
                    handler_input.response_builder.speak(
                        "I couldn't get your location. Please try again."
                    )
                    .set_should_end_session(True)
                    .response
                )

            latitude = geolocation.coordinate.latitude_in_degrees
            longitude = geolocation.coordinate.longitude_in_degrees

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
            logger.exception(f"Error trying to get prayer times: {e}")
            return (
                handler_input.response_builder.speak(
                    "Sorry, I couldn't fetch the prayer times at the moment."
                )
                .set_should_end_session(True)
                .response
            )


sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SetMuezzinIntentHandler())
sb.add_request_handler(GetPrayerTimesIntentHandler())


def lambda_handler(event, context):
    return sb.lambda_handler()(event, context)
