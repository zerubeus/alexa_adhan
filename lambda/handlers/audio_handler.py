from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_request_type


class AudioPlayerEventHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (
            is_request_type("AudioPlayer.PlaybackStarted")(handler_input)
            or is_request_type("AudioPlayer.PlaybackFinished")(handler_input)
            or is_request_type("AudioPlayer.PlaybackStopped")(handler_input)
            or is_request_type("AudioPlayer.PlaybackFailed")(handler_input)
        )

    def handle(self, handler_input):
        return handler_input.response_builder.response
