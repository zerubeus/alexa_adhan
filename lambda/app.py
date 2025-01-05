from ask_sdk_core.skill_builder import SkillBuilder

from services.request_handlers import SetMuezzinIntentHandler
from services.request_handlers import LaunchRequestHandler
from services.request_handlers import SessionEndedRequestHandler
from services.request_handlers import ConnectionsResponseHandler
from services.request_handlers import GetPrayerTimesIntentHandler
from services.request_handlers import HelpIntentHandler
from services.request_handlers import CancelAndStopIntentHandler
from services.request_handlers import FallbackIntentHandler
from services.request_handlers import EnableNotificationsIntentHandler

sb = SkillBuilder()


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
