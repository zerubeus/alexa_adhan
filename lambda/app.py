import boto3
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model.ui import SimpleCard
from services.prayer_service import PrayerService

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


class GetPrayerTimesIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetPrayerTimesIntent")(handler_input)

    def handle(self, handler_input):
        # Example coordinates for New York
        latitude = 40.7128
        longitude = -74.0060

        try:
            prayer_times = PrayerService.get_prayer_times(latitude, longitude)
            formatted_times = PrayerService.format_prayer_times(prayer_times)

            speech_text = f"Here are today's prayer times: {formatted_times}"

            return (
                handler_input.response_builder.speak(speech_text)
                .set_card(SimpleCard("Prayer Times", speech_text))
                .set_should_end_session(True)
                .response
            )

        except Exception as e:
            speech_text = "Sorry, I couldn't fetch the prayer times at the moment."
            return (
                handler_input.response_builder.speak(speech_text)
                .set_should_end_session(True)
                .response
            )


sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SetMuezzinIntentHandler())
sb.add_request_handler(GetPrayerTimesIntentHandler())


def lambda_handler(event, context):
    return sb.lambda_handler()(event, context)
