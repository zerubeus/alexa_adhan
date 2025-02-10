import datetime
from typing import List, Tuple

import pytz
from ask_sdk_model.interfaces.connections import SendRequestDirective
from ask_sdk_model.services import ServiceException
from ask_sdk_model.services.reminder_management import (
    Trigger,
    TriggerType,
    Recurrence,
    RecurrenceFreq,
    ReminderRequest,
    AlertInfo,
    SpokenInfo,
    SpokenText,
    PushNotification,
    PushNotificationStatus,
)
from aws_lambda_powertools import Logger

from auth.auth_permissions import permissions
from services.geolocation_service import get_device_location
from services.prayer_times_service import PrayerService
from speech_text import get_speech_text

logger = Logger(service="prayer_notification_service")


class PrayerNotificationService:
    @staticmethod
    def get_permission_status(permissions_obj, permission_key):
        """Get the status of a specific permission."""
        if not permissions_obj or not hasattr(permissions_obj, "scopes"):
            return None

        scopes = permissions_obj.scopes
        if not isinstance(scopes, dict):
            return None

        permission_data = scopes.get(permission_key, {})
        if not isinstance(permission_data, dict):
            return None

        return permission_data.get("status")

    @staticmethod
    def check_reminder_permission(alexa_permissions):
        """Check if the user has granted reminder permissions."""
        has_reminder_permission = (
            PrayerNotificationService.get_permission_status(
                alexa_permissions, permissions["reminder_rw"]
            )
            == "GRANTED"
        )

        if has_reminder_permission:
            return True

        logger.info(
            "Reminder permissions not found in scopes or not granted",
            extra={
                "has_permissions": bool(alexa_permissions),
                "has_scopes": (
                    hasattr(alexa_permissions, "scopes") if alexa_permissions else False
                ),
                "scopes": (
                    alexa_permissions.scopes
                    if (alexa_permissions and hasattr(alexa_permissions, "scopes"))
                    else None
                ),
                "reminder_permission": permissions["reminder_rw"],
            },
        )
        return False

    @staticmethod
    def request_reminder_permission(response_builder, texts):
        """Request reminder permission from the user."""
        return response_builder.add_directive(
            SendRequestDirective(
                name="AskFor",
                payload={
                    "@type": "AskForPermissionsConsentRequest",
                    "@version": "2",
                    "permissionScopes": [
                        {
                            "permissionScope": permissions["reminder_rw"],
                            "consentLevel": "ACCOUNT",
                        }
                    ],
                },
                token="user_reminder_permission",
            )
        ).response

    @staticmethod
    def setup_prayer_reminders(
        prayer_times: dict,
        reminder_service,
        user_timezone: pytz.timezone,
        locale: str = "en-US",
    ) -> Tuple[List[dict], str]:
        """Set up daily prayer reminders for each prayer time.

        Args:
            prayer_times: Dictionary of prayer times
            reminder_service: Alexa reminder management service
            user_timezone: User's timezone
            locale: User's locale

        Returns:
            Tuple containing list of created reminders and formatted times string

        Raises:
            ServiceException: If there are issues creating reminders
        """
        reminders = []
        formatted_times = []
        texts = get_speech_text(locale)

        logger.info(
            "Starting to set up prayer reminders",
            extra={
                "num_prayers": len(PrayerService.PRAYERS),
                "timezone": str(user_timezone),
                "locale": locale,
                "prayer_times": prayer_times,
            },
        )

        for prayer in PrayerService.PRAYERS:
            if prayer in prayer_times:
                prayer_time = datetime.datetime.strptime(
                    prayer_times[prayer], "%H:%M"
                ).time()

                now = datetime.datetime.now(user_timezone)
                today = now.date()

                reminder_time = user_timezone.localize(
                    datetime.datetime.combine(today, prayer_time)
                )

                if reminder_time < now:
                    reminder_time = user_timezone.localize(
                        datetime.datetime.combine(
                            today + datetime.timedelta(days=1), prayer_time
                        )
                    )

                formatted_times.append(
                    f"{prayer} at {prayer_time.strftime('%I:%M %p')}"
                )

                notification_time = reminder_time.strftime("%Y-%m-%dT%H:%M:%S")

                logger.info(
                    f"Setting up reminder for {prayer}",
                    extra={
                        "prayer": prayer,
                        "notification_time": notification_time,
                        "timezone": str(user_timezone),
                        "reminder_time": str(reminder_time),
                        "current_time": str(now),
                    },
                )

                trigger = Trigger(
                    object_type=TriggerType.SCHEDULED_ABSOLUTE,
                    scheduled_time=notification_time,
                    time_zone_id=str(user_timezone),
                    recurrence=Recurrence(freq=RecurrenceFreq.DAILY, interval=1),
                )

                reminder_text = texts.PRAYER_TIME_REMINDER.format(prayer)
                text = SpokenText(locale=locale, text=reminder_text)
                alert_info = AlertInfo(SpokenInfo([text]))
                push_notification = PushNotification(PushNotificationStatus.ENABLED)

                reminder_request = ReminderRequest(
                    request_time=datetime.datetime.now(pytz.UTC).isoformat(),
                    trigger=trigger,
                    alert_info=alert_info,
                    push_notification=push_notification,
                )

                logger.info(
                    f"Creating reminder for {prayer}",
                    extra={
                        "prayer": prayer,
                        "reminder_request": str(reminder_request),
                        "trigger_time": notification_time,
                    },
                )

                reminder = reminder_service.create_reminder(reminder_request)
                reminders.append(reminder)

                logger.info(
                    f"Successfully created reminder for {prayer}",
                    extra={
                        "prayer": prayer,
                        "reminder_id": getattr(reminder, "alert_token", None),
                        "reminder_status": getattr(reminder, "status", None),
                    },
                )

        logger.info(
            "Completed setting up reminders",
            extra={
                "num_reminders_created": len(reminders),
                "formatted_times": formatted_times,
            },
        )
        return reminders, ", ".join(formatted_times)

    @staticmethod
    def setup_prayer_notifications(handler_input):
        """Set up prayer notifications for the user."""
        try:
            req_envelope = handler_input.request_envelope
            response_builder = handler_input.response_builder
            locale = handler_input.request_envelope.request.locale
            texts = get_speech_text(locale)

            # Get device location
            success, location_result = get_device_location(
                req_envelope,
                response_builder,
                handler_input.service_client_factory,
            )

            if not success:
                logger.error(
                    "Failed to get device location",
                    extra={"location_result": str(location_result)},
                )
                return location_result

            latitude, longitude = location_result

            logger.info(
                "Successfully got device location",
                extra={"latitude": latitude, "longitude": longitude},
            )

            # Get prayer times
            prayer_times = PrayerService.get_prayer_times(latitude, longitude)

            if not prayer_times:
                logger.error("Failed to get prayer times after retries")
                return response_builder.speak(texts.ERROR).response

            # Get user timezone
            device_id = req_envelope.context.system.device.device_id

            try:
                timezone = handler_input.service_client_factory.get_ups_service().get_system_time_zone(
                    device_id
                )

                user_timezone = pytz.timezone(timezone)
                logger.info("Got user timezone", extra={"timezone": timezone})
            except Exception as e:
                logger.error(
                    "Failed to get user timezone",
                    extra={
                        "error_type": type(e).__name__,
                        "error": str(e),
                        "device_id": device_id,
                    },
                )

                return response_builder.speak(texts.ERROR).response

            # Set up reminders
            try:
                reminder_service = (
                    handler_input.service_client_factory.get_reminder_management_service()
                )

                logger.info("prayer_notification_service: Setting up prayer reminders")

                reminders, formatted_times = (
                    PrayerNotificationService.setup_prayer_reminders(
                        prayer_times,
                        reminder_service,
                        user_timezone,
                        locale=locale,
                    )
                )

                logger.info(
                    "Successfully set up reminders",
                    extra={
                        "num_reminders": len(reminders),
                        "formatted_times": formatted_times,
                    },
                )

                return response_builder.speak(
                    texts.REMINDER_SETUP_CONFIRMATION.format(formatted_times)
                ).response
            except ServiceException as e:
                logger.error(
                    "Failed to set up reminders",
                    extra={
                        "error": str(e),
                        "status_code": getattr(e, "status_code", None),
                        "error_type": type(e).__name__,
                        "traceback": True,
                    },
                )

                if e.status_code == 401:
                    # 401 typically means no permission (or skill manifest not updated)
                    # If it still fails here, either the user closed the permission prompt,
                    # or Alexa hasn't fully updated the token for this single invocation.
                    logger.info("Asking user to enable reminder permissions")

                    return response_builder.speak(
                        texts.NOTIFY_MISSING_REMINDER_PERMISSIONS
                    ).response
                elif e.status_code == 403:
                    logger.info("Max reminders limit reached")
                    return response_builder.speak(texts.MAX_REMINDERS_ERROR).response

                return response_builder.speak(texts.ERROR).response

            # Return success response
            confirmation_text = texts.REMINDER_SETUP_CONFIRMATION.format(
                formatted_times
            )

            play_directive = PrayerService.get_adhan_directive()

            return (
                response_builder.speak(confirmation_text)
                .add_directive(play_directive)
                .set_should_end_session(True)
                .response
            )

        except Exception as e:
            logger.exception(
                f"Failed to set up prayer reminders: {str(e)}",
            )

            return handler_input.response_builder.speak(texts.ERROR).response

    @staticmethod
    def handle_connections_response(handler_input):
        """Handle the Connections.Response for reminder permission requests."""
        request = handler_input.request_envelope.request
        locale = handler_input.request_envelope.request.locale
        texts = get_speech_text(locale)

        logger.info(
            "Handling Connections.Response",
            extra={
                "request_id": handler_input.request_envelope.request.request_id,
                "request_name": request.name,
                "status_code": request.status.code,
                "payload_status": (
                    request.payload.get("status") if request.payload else None
                ),
                "locale": locale,
            },
        )

        # Ensure it's the response to our "AskFor" directive and status code == 200
        if request.name == "AskFor" and request.status.code == "200":
            status = request.payload.get("status")
            if status == "ACCEPTED":
                logger.info("User accepted the reminder permission request.")

                # Instead of setting up reminders now, politely let them know they're set
                # for next time
                return (
                    handler_input.response_builder.speak(
                        texts.PERMISSIONS_ACCEPTED_REINVITE
                    )
                    .set_should_end_session(True)
                    .response
                )
            else:
                # The user denied or something else
                logger.info("User denied the permission request")
                return (
                    handler_input.response_builder.speak(texts.PERMISSION_DENIED)
                    .set_should_end_session(True)
                    .response
                )

        # Any other type of Connections.Response or non-200 just end politely
        logger.error(
            "Invalid request",
            extra={"request_name": request.name, "status_code": request.status.code},
        )
        return handler_input.response_builder.speak(texts.ERROR).response
