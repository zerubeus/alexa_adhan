class SpeechText:
    WELCOME = "Bienvenue dans Heures de Prière!"
    WHAT_DO_YOU_WANT = "Que puis-je faire pour vous?"
    NOTIFY_MISSING_LOCATION_PERMISSIONS = "Pour obtenir les heures de prière, j'ai besoin d'accéder à votre localisation. Dites 'Ok Alexa, activer la localisation' pour activer cette permission."
    NOTIFY_MISSING_REMINDER_PERMISSIONS = (
        "Pour configurer les rappels par la voix, dites 'Activer notifications'."
    )
    NO_LOCATION = "Je n'ai pas pu obtenir votre localisation. Veuillez vérifier vos paramètres de localisation dans l'application Alexa."
    ERROR = "Désolé, une erreur s'est produite. Veuillez réessayer!"
    LOCATION_FAILURE = "Je n'ai pas pu obtenir votre localisation. Veuillez vérifier vos paramètres de localisation et réessayer."
    HELP_TEXT = "Vous pouvez me demander les heures de prière ou configurer des notifications de prière. Par exemple, essayez de dire : quelles sont les heures de prière?"
    FALL_BACK_TEXT = "Désolé, je n'ai pas compris. Veuillez réessayer."
    NOTIFICATION_SETUP_TEXT = "J'ai configuré les notifications pour les heures de prière. Vous recevrez une notification avant chaque prière."
    GOODBYE = "Au revoir!"
    ASK_REMINDER_PERMISSION = (
        "Voulez-vous que je configure des rappels quotidiens pour les heures de prière?"
    )
    MAX_REMINDERS_ERROR = "Désolé, vous avez atteint le nombre maximum de rappels. Veuillez supprimer des rappels existants et réessayer."
    REMINDER_SETUP_CONFIRMATION = "Je vais configurer des rappels quotidiens de prière"
    PERMISSION_DENIED = "D'accord, je ne configurerai pas de rappels. Vous pouvez me le redemander à tout moment si vous changez d'avis."
    PRIER_TIMES = "Les heures de prière pour aujourd'hui sont : {}."
    LOCATION_TEXT = " à {}."
    PRAYER_TIME_REMINDER = "L'heure de la prière {} est arrivée"
    REMINDER_PERMISSION_ALREADY_GRANTED = "Vous avez déjà les permissions pour les rappels. Voulez-vous configurer des rappels quotidiens pour les heures de prière?"
    REMINDER_PERMISSION_NOT_READY = "Vous n'avez pas les permissions pour les rappels. Veuillez activer les notifications pour configurer des rappels."
    PERMISSIONS_ACCEPTED_REINVITE = (
        "Parfait ! Vos permissions ont été mises à jour. "
        "Veuillez dire 'Activer notifications' à nouveau, et je configurerai vos rappels de prière."
    )
