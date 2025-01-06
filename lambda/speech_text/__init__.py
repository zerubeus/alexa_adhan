def get_speech_text(locale):
    if locale == "fr-FR":
        from speech_text.fr_speech_text import SpeechText
    else:
        from speech_text.en_speech_text import SpeechText
    return SpeechText
