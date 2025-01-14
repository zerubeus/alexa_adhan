class SpeechText:
    WELCOME = "Welcome to Prayer Times!"
    WHAT_DO_YOU_WANT = "What can I help you with?"
    NOTIFY_MISSING_PERMISSIONS = "To get prayer times, I need access to your location. I've sent a card to help you enable this permission."
    NO_LOCATION = "I couldn't get your location. Please check your location settings in the Alexa app."
    ERROR = "Sorry, something went wrong. Please try again!"
    LOCATION_FAILURE = "I couldn't get your location. Please check your location settings and try again."
    HELP_TEXT = "You can ask me for prayer times or set up prayer notifications. For example, try saying: what are the prayer times?"
    FALL_BACK_TEXT = "Sorry, I didn't understand that. Please try again."
    NOTIFICATION_SETUP_TEXT = "I've set up notifications for prayer times. You'll receive a notification before each prayer."
    GOODBYE = "Goodbye!"
    ASK_REMINDER_PERMISSION = "Would you like me to set up daily prayer time reminders? I'll notify you 10 minutes before each prayer time."
    MAX_REMINDERS_ERROR = "Sorry, you've reached the maximum number of reminders. Please delete some existing reminders and try again."
    REMINDER_SETUP_CONFIRMATION = (
        "I'll set up daily reminders for the following prayer times: {}"
    )
    PERMISSION_DENIED = "Okay, I won't set up any reminders. You can ask me again anytime if you change your mind."
    PRIER_TIMES = "The prayer times for today are: Fajr at {}, Dhuhr at {}, Asr at {}, Maghrib at {}, Isha at {}."
