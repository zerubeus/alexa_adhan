from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.api_client import DefaultApiClient

from services.request_handlers import (
    SetMuezzinIntentHandler,
    LaunchRequestHandler,
    SessionEndedRequestHandler,
    GetPrayerTimesIntentHandler,
    HelpIntentHandler,
    CancelAndStopIntentHandler,
    FallbackIntentHandler,
    EnableNotificationsIntentHandler,
    GetPrayerTimesExceptionHandler,
    CatchAllExceptionHandler,
)

sb = CustomSkillBuilder(api_client=DefaultApiClient())

# Add request handlers
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SetMuezzinIntentHandler())
sb.add_request_handler(GetPrayerTimesIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelAndStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(EnableNotificationsIntentHandler())

# Add exception handlers
sb.add_exception_handler(GetPrayerTimesExceptionHandler())
sb.add_exception_handler(CatchAllExceptionHandler())


def lambda_handler(event, context):
    return sb.lambda_handler()(event, context)
