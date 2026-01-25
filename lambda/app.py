from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_core.skill_builder import CustomSkillBuilder
from handlers.request_handler import (
    CancelAndStopIntentHandler,
    CatchAllExceptionHandler,
    ConnectionsResponseHandler,
    EnableNotificationsIntentHandler,
    FallbackIntentHandler,
    GetNextPrayerTimeIntentHandler,
    GetPrayerTimesExceptionHandler,
    GetPrayerTimesIntentHandler,
    HelpIntentHandler,
    LaunchRequestHandler,
    SessionEndedRequestHandler,
)

sb = CustomSkillBuilder(api_client=DefaultApiClient())

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GetPrayerTimesIntentHandler())
sb.add_request_handler(GetNextPrayerTimeIntentHandler())
sb.add_request_handler(EnableNotificationsIntentHandler())
sb.add_request_handler(ConnectionsResponseHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelAndStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(FallbackIntentHandler())

sb.add_exception_handler(GetPrayerTimesExceptionHandler())
sb.add_exception_handler(CatchAllExceptionHandler())


handler = sb.lambda_handler()
