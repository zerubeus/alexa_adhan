class SpeechText:
    WELCOME = "Welcome to Prayer Times!"
    WHAT_DO_YOU_WANT = "What can I help you with?"
    NOTIFY_MISSING_LOCATION_PERMISSIONS = "To get prayer times, I need access to your location. Say 'Ok Alexa, enable location' to enable this permission."
    NOTIFY_MISSING_REMINDER_PERMISSIONS = (
        "To set up voice reminders, say 'Enable notifications'."
    )
    NO_LOCATION = "I couldn't get your location. Please check your location settings in the Alexa app."
    ERROR = "Sorry, something went wrong. Please try again!"
    LOCATION_FAILURE = "I couldn't get your location. Please check your location settings and try again."
    HELP_TEXT = "You can ask me for prayer times or set up prayer notifications. For example, try saying: what are the prayer times?"
    FALL_BACK_TEXT = "Sorry, I didn't understand that. Please try again."
    NOTIFICATION_SETUP_TEXT = "I've set up notifications for prayer times. You'll receive a notification before each prayer."
    GOODBYE = "Goodbye!"
    ASK_REMINDER_PERMISSION = "Would you like me to set up daily prayer time reminders?"
    MAX_REMINDERS_ERROR = "Sorry, you've reached the maximum number of reminders. Please delete some existing reminders and try again."
    REMINDER_SETUP_CONFIRMATION = (
        "I'll set up daily reminders for the following prayer times: {}"
    )
    PERMISSION_DENIED = "Okay, I won't set up any reminders. You can ask me again anytime if you change your mind."
    PRIER_TIMES = "The prayer times for today are: {}."
    PRAYER_TIME_REMINDER = "Time for {} prayer"
    LOCATION_TEXT = " in {}."
    REMINDER_PERMISSION_ALREADY_GRANTED = "You already have reminders permission! Would you like to set up a daily reminder?"
    REMINDER_PERMISSION_NOT_READY = "You don't have reminders permission yet. Please enable notifications to set up reminders."
