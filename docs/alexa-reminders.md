# Related doc for implementing Alexa reminders

Your skill can create and manage reminders for your customers by using Alexa reminders. A skill requires explicit customer permission to create reminders and can only modify, edit, and delete reminders that the skill itself has created for that customer.

User experience for skill reminders
With the customer's permission, your skill can set a reminder for a predetermined time, and then, at this time, Alexa wakes up and reads the reminder to the customer.

Alexa "barges in" to whatever interaction a customer might be having with Alexa at that moment. If the customer isn't expecting this reminder, the interruption might be disruptive. To protect customers from unexpected barge-ins, a skill must acquire two sets of permissions to create a reminder:

Global Reminders Read/Write permission, that the skill requests from the user after skill enablement.
Explicit customer permission for setting each specific reminder.
Your skill should obtain explicit permission as part of the dialog that your skill has with the customer. For example, you might ask the customer, "Would you like me to remind you?" or "Do you want me to remind you of this?" The skill response must clarify to the customer about the reminder time, and include the reminder recurrence, if defined.

When a reminder is due to go off, Alexa plays a brief tone on the customer's Alexa-enabled device, and then says, "Here's your reminder….," along with label information. The reminder repeats twice unless the customer says, "Stop."

A sample uninterrupted reminder flow:

Alexa plays a brief tone at the reminder time.
Alexa says, "Here's your reminder. You have an upcoming reservation at Fizzy-Foo today at 8.00 PM. You have an upcoming reservation at Fizzy-Foo today at 8.00 PM."
You can't customize the voice delivery for the reminders. However, when you create the reminder, you can set whether the reminder should also enable a mobile notification.

The customer sees reminders in the Alexa app until three days after completion, after which the reminders are automatically deleted.

If the customer hasn't granted reminders permission to the skill, make sure that your skill gracefully informs the customer how to grant permissions and that the skill sends the customer a home card providing a link to the skill permissions page in the Alexa app.

Reminder types
Your skill can create a one-time or recurring reminder. If a recurring reminder, your skill can set the reminder to occur on a daily, weekly, monthly, or yearly basis, or on specific days.

How trigger times are calculated
Your skill can create a reminder that has an absolute time, which means it occurs at a specified time, or a reminder with a relative time, which means that it occurs a specified amount of time after another event.

Absolute calculations
Use absolute time to set a reminder to a fixed pre-calculated time, for example, to remind someone to take medicine on June 1, 2019 at 7 PM.

To set this reminder, use a SCHEDULED_ABSOLUTE reminder and a fixed value for the mandatory scheduledTime field.

"requestTime" : "2019-09-22T19:04:00.672",
"trigger": {
"type" : "SCHEDULED_ABSOLUTE",
"scheduledTime" : "2019-06-01T19:00:00"
}
Relative calculations
Use an offset to set a reminder to a relative, duration-based time, for example, to remind someone to take medicine in one hour.

To set this reminder, use a SCHEDULED_RELATIVE reminder and an offset in seconds. The ring time calculates by comparing the requestedTime to the offsetInSeconds that the skill sets.

"requestTime" : "2019-09-22T19:04:00.672",
"trigger": {
"type" : "SCHEDULED_RELATIVE",
"offsetInSeconds" : "7200"
}
Setting time zones for absolute times
You can set a reminder in the time zone of the Alexa-enabled device, or in the time zone of your app or service.

To set a reminder in the same time zone of the device, include the scheduledTime. You don't have to set the timezoneId field. The following example sets the reminder at 7 PM in the time zone of the device.

"scheduledTime" : "2019-06-01T19:00:00"
To set a reminder in the time zone of the app, provide the absolute time and the time zone for when the reminder should occur. The following example sets a reminder for a reservation on June 1, 2019 at 7 PM in New York.

"scheduledTime" : "2019-06-01T19:00:00"
"timezoneId" : "America/New_York"
Note: For speech and display purposes, Alexa always uses the original time zone of the device, rather then the timestamp in the app request. This translation typically occurs if the users device isn't in the same time zone as the app request. For example, if the customer's device is in PDT (Los Angeles), a time of 2019-06-01T19:00:00 in America/New_York speaks and displays as 4 PM PDT.
Steps to add reminders to your skill
Complete the following steps to integrate your custom skill with Alexa reminders.

To add reminders to your custom skill

If you created your skill in the developer console, to ask the user for reminders permissions, on the Build page, in the left pane, select TOOLS > Permissions or PERMISSIONS, and then toggle Reminders.
Or, if you edit the skill manifest directly, add the alexa::alerts:reminders:skill:readwrite permission.
Implement reminders capabilities in your skill service code.
Use the Reminders REST API to create a new reminder skill or to update your existing custom skill to subscribe to reminder events.
Request Alexa reminders permission from the customer and use the APIs to read and update Alexa reminders. A skill can only access reminders that the skill itself has created.
Follow the instructions to Use Events in Your Skill Service to set up your skill.json manifest file for reminder events. For more details, see Reminder events.
Implement handlers to consume and respond to reminder events.
Send a card to the Alexa app that indicates the reminder was delivered. For more details, see Include a Card in Your Skill's Response.
The following card shows an example reminder.
Format for reminder card in the Alexa app
Manage permissions with an apiAccessToken
When your skill uses the Reminders API to create a reminder, your skill must provide an in-session ID where explicit customer permission was granted. If a skill violates the permission policy, reminders access for the skill is revoked. You can't use an out-of-session token to create a reminder, but you can use the out-of-session token to edit or delete a reminder.

If your skill doesn't have explicit customer permission when the customer invokes your skill, it must obtain permission either by following a voice permissions workflow, or by sending a permissions card to the customer. To set up voice permissions, see Set Up Voice Permissions for Reminders. To set up permissions by card, see Permissions card for requesting customer consent. The scope for reminders is alexa::alerts:reminders:skill:readwrite.

Each request sent to your skill includes an API access token that encapsulates the permissions granted to your skill. Retrieve this token for use when you call the API to create or edit a reminder.

The following example shows the context.System.apiAccessToken in the request message. For the full body of the request, see Request Format.

```json
{
  "context": {
    "System": {
      "apiAccessToken": "AxThk...",
      "apiEndpoint": "https://api.amazonalexa.com",
      "device": {
        "deviceId": "string-identifying-the-device",
        "supportedInterfaces": {}
      },
      "application": {
        "applicationId": "string"
      },
      "user": {}
    }
  }
}
```

The following example shows how to get the access token in Node.js.

```js
accessToken = this.event.context.System.apiAccessToken
```

## Set Up Voice Permissions for Reminders

With voice permissions for reminders, your skill can ask the user, via voice, for this particular permission. After the skill initiates the request, Alexa prompts the user as to whether they want to grant permission to create a specific reminder. The user responds, and if the user grants this permission, the skill can then create the reminder. If the user does not grant this permission, then the skill cannot create a reminder. Your skill should provide a fallback workflow if the user does not grant permission to create a reminder.

Voice permissions for reminders make your skill more convenient to your users. The skill does not have to send a card to the Alexa app when requesting permissions for reminders, and the user does not have to open the Alexa app to grant permissions to the skill.

Standard voice permission workflows
A skill initiates the initial prompt asking if the user wants to set a reminder. You can determine when your skill should ask the user if they want to set a reminder.

User grants permission by voice to reminders
In this example, the skill is linked to a third-party sports news app called Sports News Example. Some of the skill's output responses are controlled by the skill, and some by Alexa.

User: Alexa, when do the Oranges play next?

Alexa (as determined by skill): The Oranges play the Apples next Thursday at 7pm. Would you like to set a reminder?

User: Yes.

Alexa (as determined by Alexa): Do you give Sports New permission to update your reminders? You can say I approve or no.

User: I approve.

Alexa (as determined by skill): I'll remind you at 7pm next Thursday to watch the Oranges versus Apples.

In this example, the skill first answers the user's question. The skill controls the content of the second sentence, "Sports News Example can give you reminders when your favorite teams play."

Alexa controls the content of the third sentence asking for permission, and as the skill developer, you cannot change the wording.

The last two sentences are part of the same response, but the second-to-last is controlled by Alexa, and the last sentence is controlled by the skill.

When the user grants permission, the skill receives a request that indicates that the permission was granted. Alexa sets the reminder. Your skill should inform the user that the reminder is set, and the skill continues its session.

User denies permission for reminders after initial agreement
In this case, the user denies permission to set a reminder, after initially agreeing to do so. Alexa acknowledges the refusal, and the skill continues its session. Note that the user here first says "Yes," before later saying "No." If the user said "No" initially, the voice permissions workflow should not start, and the skill would continue its session as before.

You cannot control Alexa's interaction with the user in respect to this permissions workflow, other than when you send out the first prompt.

User: Alexa, when do the Oranges play next?

Alexa (as determined by skill): The Oranges play the Apples next Thursday at 7pm. Would you like to set a reminder?

User: Yes.

Alexa (as determined by Alexa): Do you give Sports News permission to update your reminders? You can say I approve or no.

User: No.

User response is unintelligible
Suppose the user, when Alexa asks for permission to set a reminder, has an unintelligible response. Alexa re-prompts the user with a rephrased question. If the user grants or denies permission after the re-prompt, the corresponding workflow then follows from that point.

User: Alexa, when do the Oranges play next?

Alexa (as determined by skill): The Oranges play the Apples next Thursday at 7pm. Would you like to set a reminder?

User: Yes.

Alexa (as determined by Alexa): Do you give Sports News permission to update your reminders? You can say I approve or no.

User: <Unintelligible>

Alexa (as determined by Alexa): Do you give Sports News permission to update your reminders? You can say I approve or no.

Standard prompts
A skill kicks off the voice permission for reminders workflow, and the skill controls the initial prompt to the user. Alexa controls the next prompts in the voice permissions workflow, which provides a consistent experience for users across skills. For clarity and easy reference, each prompt has been given a tag. Your skill should follow the AcceptConsentReminders prompt with a restatement of the reminder, its date and time, and its purpose, and your skill controls this portion of the response.

AskForConsentReminders: Alexa (as determined by Alexa): Do you give [skillName] permission to update your reminders? You can say I approve or no.

AskForConsentRetryReminders: Alexa (as determined by Alexa): Do you give [skillName] permission to update your reminders? You can say I approve or no.

Send a Connections.SendRequest directive
When the user responds affirmatively when the skill asks to set a reminder, your skill service code can then send a Connections.SendRequest directive, as shown here. The permissionScope value is for the reminders scope: alexa::alerts:reminders:skill:readwrite.

The token field in this directive is not used by Alexa, but the token value is returned in the resulting Connections.Response request. You can provide this token in a format that makes sense for the skill, and you can use an empty string if you do not need it.

The consentLevel parameter is the granularity of the user to which to ask for the consent. Valid values are ACCOUNT and PERSON:

ACCOUNT is the Amazon account holder to which the Alexa-enabled device is registered.
PERSON is the recognized speaker. For details about recognized speakers, see Add Personalization to Your Alexa Skill.

```json
{
  "type": "Connections.SendRequest",
  "name": "AskFor",
  "payload": {
    "@type": "AskForPermissionsConsentRequest",
    "@version": "2",
    "permissionScopes": [
      {
        "permissionScope": "alexa::alerts:reminders:skill:readwrite",
        "consentLevel": "ACCOUNT"
      }
    ]
  },
  "token": ""
}
```

Note: Version 1 of the API (in which payload.permissionScopes is not a list, and Alexa has different speech prompts) still works. However, for new implementations, use the current format of the API shown previously.
After receiving this directive, Alexa asks the user to grant permission for the specified reminders permission scope, which results in a Connections.Response request, as shown. The body.status value is one of:

ACCEPTED – the user has granted the permissions, either in response to the last request or previously.
DENIED – the user has refused the permissions.
NOT_ANSWERED – the user did not answer the request for permissions, or the response was not understood. In this case, Alexa will re-prompt the user.

```json
{
  "type": "Connections.Response",
  "requestId": "string",
  "timestamp": "string",
  "locale": "string",
  "name": "AskFor",
  "status": {
    "code": "string",
    "message": "string"
    },
  "token": "string",
  "payload": {
    "permissionScopes" : [
      {
        "permissionScope" : "alexa::alerts:reminders:skill:readwrite",
        "consentLevel": "ACCOUNT"
      },
      "status" : <status enum> // ACCEPTED, DENIED, or NOT_ANSWERED
    ]
  }
}
```

Note: Version 1 of the API (in which payload.permissionScopes is not a list) still works. However, for new implementations, use the current format of the API shown previously.
As you can see in the examples, Alexa has a set of standard prompts that you cannot change when you develop a skill. You do not have to code these prompts, as they are included with the standard voice permissions workflow.

Code example for a voice permissions request
The following example shows how you can add code to an AWS Lambda function to send the Connections.SendRequest directive for a voice permissions request. You can use the token field to keep track of state. Any value that you provide in the token field appears in the user's requests to Alexa. For example, you could use the token field to store the userId value. You can also set the token to be an empty string.

Node.js SDK v2
Node.js SDK v1
Raw JSON

This code example uses the Alexa Skills Kit SDK for Node.js (v2).

```js
return handlerInput.responseBuilder
  .addDirective({
    type: "Connections.SendRequest",
    name: "AskFor",
    payload: {
      "@type": "AskForPermissionsConsentRequest",
      "@version": "2",
      permissionScopes: [
        {
          permissionScope: "alexa::alerts:reminders:skill:readwrite",
          consentLevel: "ACCOUNT"
        }
      ]
    },
    token: "<token string>"
  })
  .getResponse()
```

Best practices for user experience of reminders
See Alexa Reminders Guidelines for Usage.

## Tutorial: Update a Reminder from Outside of an Alexa Skill Session

Note: Sign in to the developer console to build or publish your skill.
The following tutorial walks you through the steps to update a user-specific reminder from outside of an Alexa skill session. For the definition of a skill session, see Manage the Skill Session and Session Attributes.

Prerequisites
Before you can update a reminder, you must have the reminder ID of the reminder you want to update. The reminder ID is the alertToken that the Reminders API returns when you create a reminder. You can also find a reminder ID by getting all reminders.

Steps to update a reminder from outside of a skill session
In the following steps, you first get the necessary credentials to call the Skill Messaging API. You then use the Skill Messaging API to send an asynchronous message to your skill. Your skill's request handler code handles the message from the Skill Messaging API and updates the reminder.

Get a client ID and client secret for your skill.
Get the user ID.
Get an access token for the Skill Messaging API.
Call the Skill Messaging API.
Update the reminder.
Step 1: Get a client ID and client secret for your skill
Before you can get an access token for the Skill Messaging API, you must have a client ID and client secret. You can get the client ID and client secret by using the developer console or by using the Alexa Skills Kit Command Line Interface (ASK CLI).

To get the client ID and client secret from the developer console

Sign in to the Alexa developer console and navigate to your skill.
On the left, under TOOLS, click Permissions.
At the bottom of the page, under Alexa Skill Messaging, copy the value from the Alexa Client ID field.
Click SHOW, and then copy the value from the Alexa Client Secret field.
To get the client ID and client secret by using the ASK CLI

At the command prompt, enter the following command.
ask smapi get-skill-credentials -s {skill Id} > credentials.json
Step 2: Get the user ID
When you call the Skill Messaging API in Step 4, you must have the user ID of the skill user. You can get the user ID from the context.System.user.userId field of any request from Alexa during a voice interaction with the user. For the location of the user ID within the request, see System object.

Step 3: Get an access token for the Skill Messaging API
You now get an access token for the Skill Messaging API by using the client ID and client secret that you found in Step 1. To get an access token, you use the Get access token with skill credentials operation. In the request body, set the scope to scope=alexa:skill_messaging.

Step 4: Call the Skill Messaging API
You now call the Skill Messaging API by using the following information:

In the path of the request, you specify the userId that you found in a user interaction in Step 2.
As the bearer token in the Authorization header of the request, you use the access_token that you found in Step 3.
In the body of the request, you specify the alertToken, which is the reminder ID mentioned in the Prerequisites.
When you call the Skill Messaging API, Alexa sends a request of type Messaging.MessageReceived to your skill. This request contains an alert token and operation that you specify in the body of the POST request to the Skill Messaging API.

To call the Skill Messaging API

Call the Skill Messaging API by using a POST request with the following format.

Header

POST /v1/skillmessages/users/{user ID} HTTP/1.1
Host: api.amazonalexa.com
Authorization: Bearer <Access token retrieved in the previous step>
Content-Type: application/json;
Body

```json
{
  "data": {
    "operation": "GET",
    "alertToken": "{alertToken}"
  },
  "expiresAfterSeconds": 36000
}
```

Step 5: Update the reminder
You now update the reminder from within your request handler code. In your request handler code, you handle the Messaging.MessageReceived request that you sent to your skill by using the Skill Messaging API in the previous step. The request includes the alertToken of the reminder to update.

The following request handler example includes code to get, delete, and update a reminder.

```js
const MessageReceived_Handler = {
  canHandle(handlerInput) {
    const { request } = handlerInput.requestEnvelope
    return request.type === "Messaging.MessageReceived"
  },

  async handle(handlerInput) {
    const { requestEnvelope, serviceClientFactory } = handlerInput
    const client = serviceClientFactory.getReminderManagementServiceClient()
    const { operation, alertToken } = requestEnvelope.request.message

    let reminder
    console.log(`[INFO] case: ${operation}`)

    try {
      switch (operation) {
        case "GET":
          if (alertToken === "") {
            // If no alertToken is present, we return all the reminders.
            const reminders = await client.getReminders()
            console.log(`[INFO] reminders: ${JSON.stringify(reminders)}`)
          } else {
            // If the alertToken is present, we return the specific reminder.
            reminder = await client.getReminder(alertToken)
            console.log(`[INFO] reminder: ${JSON.stringify(reminder)}`)
          }

          break

        case "DELETE":
          const res = await client.deleteReminder(alertToken)
          console.log(`[INFO] delete response: ${JSON.stringify(res)}`)

          break

        case "UPDATE":
          // Before updating the reminder, we need to retrieve it from the service.
          reminder = await client.getReminder(alertToken)
          console.log(`[INFO] reminder: ${JSON.stringify(reminder)}`)

          // Change the text content of the reminder.
          reminder.alertInfo.spokenInfo.content[0].text =
            "This is the new reminder message"

          // Send the reminder update.
          const reminderResponse = await client.updateReminder(
            alertToken,
            reminder
          )
          console.log(
            `[INFO] reminderResponse: ${JSON.stringify(reminderResponse)}`
          )

          break
      }
    } catch (error) {
      console.log(error)
    }
  }
}
```

### Alexa Reminders Guidelines for Usage

Reminders are prearranged messages that Alexa speaks to the customer at a specific time.

If you want to use Alexa to create reminders for a customer who uses your skill, you must obtain their informed consent every time you create a reminder on their behalf. The wording of your request must accurately and completely represent the action that you will take on the customer's behalf, so that the customer won't be surprised by the outcome.

For more details about reminders, see Alexa Reminders Overview.

Reminder examples
The following table shows example reminders for some skill categories.

Skill category Example request Example confirmation Reminder created
Business & Finance Alexa: Would you like me to remind you to check your account balance every Thursday at 8 AM? Alexa: OK, I'll remind you every Thursday at 8 AM. Text: Check your account balance
Scheduled Time: 8 AM
Recurrence Rule: Every Thursday
Education & Reference Alexa: Would you like a reminder to meditate every day at 7:00 PM? Alexa: OK, I'll remind you every day at 7:00 PM. Text: Start your meditation
Scheduled Time: 7:00 PM
Recurrence Rule: Every day
Games, Trivia & Accessories Alexa: Would you like a reminder to start your daily quiz every day at 7:30 PM? Alexa: OK, I'll remind you every day at 7:30 PM. Text: Start your daily quiz
Scheduled Time: 7:30 PM
Recurrence Rule: Every day
Lifestyle Alexa: Would you like a reminder to walk for 20 minutes every day at noon? Alexa: OK, I'll remind you every day at noon. Text: Walk for 20 minutes
Scheduled Time: 12 PM
Recurrence Rule: Every weekday
Local Alexa: Would you like me to remind you two hours before your dinner reservation? Alexa: OK, I'll remind you Friday at 5 PM. Text: Dinner at Chez Alexa 7 PM
Scheduled Time: Friday at 5 PM
Sports Alexa: Would you like a reminder to check your fantasy league team tomorrow at 6 PM? Alexa: OK, I'll remind you tomorrow at 6 PM. Text: Check your fantasy league team
Scheduled Time: Tomorrow at 6 PM
Travel & Transportation Alexa: Would you like me to remind you to check the train status on weekdays at 7 AM? Alexa: OK, I'll remind you every weekday at 7 AM. Text: Ask MyTransitSkill for the train status
Scheduled Time: 7 AM
Recurrence Rule: Every weekday
Reminder label guidelines
Review the following guidelines for creating reminders.

Guideline for reminder text Do Don't
Be concise and lead with the most critical information. Alexa announces lengthy reminders, but they might be visually truncated on small device screens, as approximately 25 characters appear per reminder on Echo Spot, including spaces. Alexa: "Here's your reminder from MyReservationSkill: Dinner at Chez Alexa 7 PM" Alexa: "Here's your reminder from MyReservationSkill: Dinner reservation at Chez Alexa at 15 Broadway Street for 4 people at 7 PM"
Be discreet. Alexa might display and announce reminders on shared devices where other people can see/hear them. Don't include personally identifiable or sensitive information in the reminder text. Examples of PII (personally identifiable information) include name, social security number, date and place of birth, and mother's maiden name. Sensitive information includes medical, educational, financial, and employment information. Alexa: "Here's your reminder from MyFinanceSkill: Pay credit card bill" Alexa: "Here's your reminder from MyFinanceSkill: Pay credit card bill for $2,415.89"
If you must refer to the user in the reminder text, use the second-person pronouns "you" and "your" rather than "me" and "my." Alexa: "This is a reminder from MySportsSkill: Check your fantasy league team." Alexa: "This is a reminder from MySportsSkill: Check my fantasy league team."
Don't include the skill name in the reminder text. Alexa: "Here's your reminder from MyTransitSkill: Check train status" Alexa: "Here's your reminder from MyTransitSkill: Ask MyTransitSkill to check train status."
Don't include unsolicited content in the reminder text, such as upselling, advertising, or other content unrelated to the reminder to which the user originally consented. Alexa: "Here's your reminder from MyLifestyleSkill: Play a 3-minute meditation" Alexa: "Here's your reminder from MyLifestyleSkill: Play a 3-minute meditation, and check out our new 15-minute option!"
Provide instructions when you submit your skill for certification
When you submit your skill for certification, use the test instructions to describe how you have implemented reminders functionality in the skill. See Submission checklist.

Best practices for setting reminders
Follow these guidelines when you use reminders in your skill. You want the customer to feel comfortable with reminders from Alexa, and to not disable your skill due to a bad experience.

Ask for permission to set a reminder at the right times
Skills should only prompt the customer for permission to create or edit reminders in the context of offering to set a reminder. The customer is more likely to grant permission if there is immediate value, such as a reminder being set, and if the suggested reminder is relevant to the conversation they are currently having with Alexa.

Provide detailed information about why your skill needs access to reminders
Skills should explicitly inform users why they need access to the reminders permissions, otherwise the skill might not pass certification.

Limit the frequency of asking for permission
You don't want your customers to feel inundated with offers to set reminders if they have previously declined permission, as they might choose to disable the skill. If a customer says "No," they shouldn't receive another offer for at least seven days.

Restate a reminder when set
If the customer grants permission, and the skill sets a reminder, make sure to restate the time and nature of the reminder so that the customer knows it has been set.

Tell customers how to grant permission at a later time
If a customer hasn't granted reminders permission to your skill, the skill should inform the customer by voice about how to grant permissions. Also, you can send a home card that provides a link to the skill permissions page.

Inform a customer of errors when your skill attempts to create, modify, or delete a reminder
When your skill attempts to create a reminder, but doesn't succeed, make sure that your skill service informs the customer that the reminder wasn't created.

If your skill attempts to modify or delete a reminder, but doesn't succeed, make sure that your skill informs the customer of the error.

Don't reuse expired reminders
When a reminder has expired, don't reuse this expired reminder by updating it, but instead create a new reminder. If appropriate, your skill can update a reminder before Alexa reads it.

# Alexa Python sdk reference for setting up reminders

Docs » <no title> » Models :ask_sdk_model package » ask_sdk_model.services package » ask_sdk_model.services.reminder_management package Edit on GitHub
ask_sdk_model.services.reminder_management package
Submodules
Note

Canonical imports have been added in the **init**.py of the package. This helps in importing the class directly from the package, than through the module.

For eg: if package a has module b with class C, you can do from a import C instead of from a.b import C.

```python
ask_sdk_model.services.reminder_management.alert_info module
class
ask_sdk_model.services.reminder_management.alert_info.
AlertInfo(spoken_info=None)
Bases: object

Alert info for VUI / GUI

Parameters: spoken_info ((optional) ask_sdk_model.services.reminder_management.alert_info_spoken_info.SpokenInfo) –
attribute_map= {'spoken_info': 'spokenInfo'}
deserialized_types= {'spoken_info': 'ask_sdk_model.services.reminder_management.alert_info_spoken_info.SpokenInfo'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.alert_info_spoken_info module
class
ask_sdk_model.services.reminder_management.alert_info_spoken_info.
SpokenInfo(content=None)
Bases: object

Parameters for VUI presentation of the reminder

Parameters: content ((optional) list[ask_sdk_model.services.reminder_management.spoken_text.SpokenText]) –
attribute_map= {'content': 'content'}
deserialized_types= {'content': 'list[ask_sdk_model.services.reminder_management.spoken_text.SpokenText]'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.error module
class
ask_sdk_model.services.reminder_management.error.
Error(code=None, message=None)
Bases: object

Parameters:
code ((optional) str) – Domain specific error code
message ((optional) str) – Detailed error message
attribute_map= {'code': 'code', 'message': 'message'}
deserialized_types= {'code': 'str', 'message': 'str'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.event module
class
ask_sdk_model.services.reminder_management.event.
Event(status=None, alert_token=None)
Bases: object

Parameters:
status ((optional) ask_sdk_model.services.reminder_management.status.Status) –
alert_token ((optional) str) –
attribute_map= {'alert_token': 'alertToken', 'status': 'status'}
deserialized_types= {'alert_token': 'str', 'status': 'ask_sdk_model.services.reminder_management.status.Status'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.get_reminder_response module
class
ask_sdk_model.services.reminder_management.get_reminder_response.
GetReminderResponse(alert_token=None, created_time=None, updated_time=None, status=None, trigger=None, alert_info=None, push_notification=None, version=None)
Bases: ask_sdk_model.services.reminder_management.reminder.Reminder

Response object for get reminder request

Parameters:
alert_token ((optional) str) – Unique id of this reminder alert
created_time ((optional) datetime) – Valid ISO 8601 format - Creation time of this reminder alert
updated_time ((optional) datetime) – Valid ISO 8601 format - Last updated time of this reminder alert
status ((optional) ask_sdk_model.services.reminder_management.status.Status) –
trigger ((optional) ask_sdk_model.services.reminder_management.trigger.Trigger) –
alert_info ((optional) ask_sdk_model.services.reminder_management.alert_info.AlertInfo) –
push_notification ((optional) ask_sdk_model.services.reminder_management.push_notification.PushNotification) –
version ((optional) str) – Version of reminder alert
attribute_map= {'alert_info': 'alertInfo', 'alert_token': 'alertToken', 'created_time': 'createdTime', 'push_notification': 'pushNotification', 'status': 'status', 'trigger': 'trigger', 'updated_time': 'updatedTime', 'version': 'version'}
deserialized_types= {'alert_info': 'ask_sdk_model.services.reminder_management.alert_info.AlertInfo', 'alert_token': 'str', 'created_time': 'datetime', 'push_notification': 'ask_sdk_model.services.reminder_management.push_notification.PushNotification', 'status': 'ask_sdk_model.services.reminder_management.status.Status', 'trigger': 'ask_sdk_model.services.reminder_management.trigger.Trigger', 'updated_time': 'datetime', 'version': 'str'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.get_reminders_response module
class
ask_sdk_model.services.reminder_management.get_reminders_response.
GetRemindersResponse(total_count=None, alerts=None, links=None)
Bases: object

Response object for get reminders request

Parameters:
total_count ((optional) str) – Total count of reminders returned
alerts ((optional) list[ask_sdk_model.services.reminder_management.reminder.Reminder]) – List of reminders
links ((optional) str) – Link to retrieve next set of alerts if total count is greater than max results
attribute_map= {'alerts': 'alerts', 'links': 'links', 'total_count': 'totalCount'}
deserialized_types= {'alerts': 'list[ask_sdk_model.services.reminder_management.reminder.Reminder]', 'links': 'str', 'total_count': 'str'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.push_notification module
class
ask_sdk_model.services.reminder_management.push_notification.
PushNotification(status=None)
Bases: object

Enable / disable reminders push notifications to Alexa mobile apps

Parameters: status ((optional) ask_sdk_model.services.reminder_management.push_notification_status.PushNotificationStatus) –
attribute_map= {'status': 'status'}
deserialized_types= {'status': 'ask_sdk_model.services.reminder_management.push_notification_status.PushNotificationStatus'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.push_notification_status module
class
ask_sdk_model.services.reminder_management.push_notification_status.
PushNotificationStatus
Bases: enum.Enum

Push notification status - Enabled/Disabled

Allowed enum values: [ENABLED, DISABLED]

DISABLED= 'DISABLED'
ENABLED= 'ENABLED'
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.recurrence module
class
ask_sdk_model.services.reminder_management.recurrence.
Recurrence(freq=None, by_day=None, interval=None, start_date_time=None, end_date_time=None, recurrence_rules=None)
Bases: object

Recurring date/time using the RFC 5545 standard in JSON object form

Parameters:
freq ((optional) ask_sdk_model.services.reminder_management.recurrence_freq.RecurrenceFreq) –
by_day ((optional) list[ask_sdk_model.services.reminder_management.recurrence_day.RecurrenceDay]) –
interval ((optional) int) – contains a positive integer representing at which intervals the recurrence rule repeats
start_date_time ((optional) datetime) – Valid ISO 8601 format - optional start DateTime of recurrence.
end_date_time ((optional) datetime) – Valid ISO 8601 format - optional end DateTime of recurrence
recurrence_rules ((optional) list[str]) –
attribute_map= {'by_day': 'byDay', 'end_date_time': 'endDateTime', 'freq': 'freq', 'interval': 'interval', 'recurrence_rules': 'recurrenceRules', 'start_date_time': 'startDateTime'}
deserialized_types= {'by_day': 'list[ask_sdk_model.services.reminder_management.recurrence_day.RecurrenceDay]', 'end_date_time': 'datetime', 'freq': 'ask_sdk_model.services.reminder_management.recurrence_freq.RecurrenceFreq', 'interval': 'int', 'recurrence_rules': 'list[str]', 'start_date_time': 'datetime'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.recurrence_day module
class
ask_sdk_model.services.reminder_management.recurrence_day.
RecurrenceDay
Bases: enum.Enum

Day of recurrence. Deprecated.

Allowed enum values: [SU, MO, TU, WE, TH, FR, SA]

FR= 'FR'
MO= 'MO'
SA= 'SA'
SU= 'SU'
TH= 'TH'
TU= 'TU'
WE= 'WE'
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.recurrence_freq module
class
ask_sdk_model.services.reminder_management.recurrence_freq.
RecurrenceFreq
Bases: enum.Enum

Frequency of recurrence. Deprecated.

Allowed enum values: [WEEKLY, DAILY]

DAILY= 'DAILY'
WEEKLY= 'WEEKLY'
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.reminder module
class
ask_sdk_model.services.reminder_management.reminder.
Reminder(alert_token=None, created_time=None, updated_time=None, status=None, trigger=None, alert_info=None, push_notification=None, version=None)
Bases: object

Reminder object

Parameters:
alert_token ((optional) str) – Unique id of this reminder alert
created_time ((optional) datetime) – Valid ISO 8601 format - Creation time of this reminder alert
updated_time ((optional) datetime) – Valid ISO 8601 format - Last updated time of this reminder alert
status ((optional) ask_sdk_model.services.reminder_management.status.Status) –
trigger ((optional) ask_sdk_model.services.reminder_management.trigger.Trigger) –
alert_info ((optional) ask_sdk_model.services.reminder_management.alert_info.AlertInfo) –
push_notification ((optional) ask_sdk_model.services.reminder_management.push_notification.PushNotification) –
version ((optional) str) – Version of reminder alert
attribute_map= {'alert_info': 'alertInfo', 'alert_token': 'alertToken', 'created_time': 'createdTime', 'push_notification': 'pushNotification', 'status': 'status', 'trigger': 'trigger', 'updated_time': 'updatedTime', 'version': 'version'}
deserialized_types= {'alert_info': 'ask_sdk_model.services.reminder_management.alert_info.AlertInfo', 'alert_token': 'str', 'created_time': 'datetime', 'push_notification': 'ask_sdk_model.services.reminder_management.push_notification.PushNotification', 'status': 'ask_sdk_model.services.reminder_management.status.Status', 'trigger': 'ask_sdk_model.services.reminder_management.trigger.Trigger', 'updated_time': 'datetime', 'version': 'str'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.reminder_created_event_request module
class
ask_sdk_model.services.reminder_management.reminder_created_event_request.
ReminderCreatedEventRequest(request_id=None, timestamp=None, locale=None, body=None)
Bases: ask_sdk_model.request.Request

Parameters:
request_id ((optional) str) – Represents the unique identifier for the specific request.
timestamp ((optional) datetime) – Provides the date and time when Alexa sent the request as an ISO 8601 formatted string. Used to verify the request when hosting your skill as a web service.
locale ((optional) str) – A string indicating the user’s locale. For example: en-US. This value is only provided with certain request types.
body ((optional) ask_sdk_model.services.reminder_management.event.Event) –
attribute_map= {'body': 'body', 'locale': 'locale', 'object_type': 'type', 'request_id': 'requestId', 'timestamp': 'timestamp'}
deserialized_types= {'body': 'ask_sdk_model.services.reminder_management.event.Event', 'locale': 'str', 'object_type': 'str', 'request_id': 'str', 'timestamp': 'datetime'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.reminder_deleted_event module
class
ask_sdk_model.services.reminder_management.reminder_deleted_event.
ReminderDeletedEvent(alert_tokens=None)
Bases: object

Parameters: alert_tokens ((optional) list[str]) –
attribute_map= {'alert_tokens': 'alertTokens'}
deserialized_types= {'alert_tokens': 'list[str]'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.reminder_deleted_event_request module
class
ask_sdk_model.services.reminder_management.reminder_deleted_event_request.
ReminderDeletedEventRequest(request_id=None, timestamp=None, locale=None, body=None)
Bases: ask_sdk_model.request.Request

Parameters:
request_id ((optional) str) – Represents the unique identifier for the specific request.
timestamp ((optional) datetime) – Provides the date and time when Alexa sent the request as an ISO 8601 formatted string. Used to verify the request when hosting your skill as a web service.
locale ((optional) str) – A string indicating the user’s locale. For example: en-US. This value is only provided with certain request types.
body ((optional) ask_sdk_model.services.reminder_management.reminder_deleted_event.ReminderDeletedEvent) –
attribute_map= {'body': 'body', 'locale': 'locale', 'object_type': 'type', 'request_id': 'requestId', 'timestamp': 'timestamp'}
deserialized_types= {'body': 'ask_sdk_model.services.reminder_management.reminder_deleted_event.ReminderDeletedEvent', 'locale': 'str', 'object_type': 'str', 'request_id': 'str', 'timestamp': 'datetime'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.reminder_management_service_client module
class
ask_sdk_model.services.reminder_management.reminder_management_service_client.
ReminderManagementServiceClient(api_configuration, custom_user_agent=None)
Bases: ask_sdk_model.services.base_service_client.BaseServiceClient

ServiceClient for calling the ReminderManagementService APIs.

Parameters: api_configuration (ask_sdk_model.services.api_configuration.ApiConfiguration) – Instance of ApiConfiguration
create_reminder(reminder_request, \*\*kwargs)
This API is invoked by the skill to create a new reminder.

Parameters:
reminder_request (ask_sdk_model.services.reminder_management.reminder_request.ReminderRequest) – (required)
full_response (boolean) – Boolean value to check if response should contain headers and status code information. This value had to be passed through keyword arguments, by default the parameter value is set to False.
Return type:
Union[ApiResponse, ReminderResponse, Error]

delete_reminder(alert_token, \*\*kwargs)
This API is invoked by the skill to delete a single reminder.

Parameters:
alert_token (str) – (required)
full_response (boolean) – Boolean value to check if response should contain headers and status code information. This value had to be passed through keyword arguments, by default the parameter value is set to False.
Return type:
Union[ApiResponse, Error]

get_reminder(alert_token, \*\*kwargs)
This API is invoked by the skill to get a single reminder.

Parameters:
alert_token (str) – (required)
full_response (boolean) – Boolean value to check if response should contain headers and status code information. This value had to be passed through keyword arguments, by default the parameter value is set to False.
Return type:
Union[ApiResponse, GetReminderResponse, Error]

get_reminders(\*\*kwargs)
This API is invoked by the skill to get a all reminders created by the caller.

Parameters: full_response (boolean) – Boolean value to check if response should contain headers and status code information. This value had to be passed through keyword arguments, by default the parameter value is set to False.
Return type: Union[ApiResponse, GetRemindersResponse, Error]
update_reminder(alert_token, reminder_request, \*\*kwargs)
This API is invoked by the skill to update a reminder.

Parameters:
alert_token (str) – (required)
reminder_request (ask_sdk_model.services.reminder_management.reminder_request.ReminderRequest) – (required)
full_response (boolean) – Boolean value to check if response should contain headers and status code information. This value had to be passed through keyword arguments, by default the parameter value is set to False.
Return type:
Union[ApiResponse, ReminderResponse, Error]

ask_sdk_model.services.reminder_management.reminder_request module
class
ask_sdk_model.services.reminder_management.reminder_request.
ReminderRequest(request_time=None, trigger=None, alert_info=None, push_notification=None)
Bases: object

Input request for creating a reminder

Parameters:
request_time ((optional) datetime) – Valid ISO 8601 format - Creation time of this reminder alert
trigger ((optional) ask_sdk_model.services.reminder_management.trigger.Trigger) –
alert_info ((optional) ask_sdk_model.services.reminder_management.alert_info.AlertInfo) –
push_notification ((optional) ask_sdk_model.services.reminder_management.push_notification.PushNotification) –
attribute_map= {'alert_info': 'alertInfo', 'push_notification': 'pushNotification', 'request_time': 'requestTime', 'trigger': 'trigger'}
deserialized_types= {'alert_info': 'ask_sdk_model.services.reminder_management.alert_info.AlertInfo', 'push_notification': 'ask_sdk_model.services.reminder_management.push_notification.PushNotification', 'request_time': 'datetime', 'trigger': 'ask_sdk_model.services.reminder_management.trigger.Trigger'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.reminder_response module
class
ask_sdk_model.services.reminder_management.reminder_response.
ReminderResponse(alert_token=None, created_time=None, updated_time=None, status=None, version=None, href=None)
Bases: object

Response object for post/put/delete reminder request

Parameters:
alert_token ((optional) str) – Unique id of this reminder alert
created_time ((optional) str) – Valid ISO 8601 format - Creation time of this reminder alert
updated_time ((optional) str) – Valid ISO 8601 format - Last updated time of this reminder alert
status ((optional) ask_sdk_model.services.reminder_management.status.Status) –
version ((optional) str) – Version of reminder alert
href ((optional) str) – URI to retrieve the created alert
attribute_map= {'alert_token': 'alertToken', 'created_time': 'createdTime', 'href': 'href', 'status': 'status', 'updated_time': 'updatedTime', 'version': 'version'}
deserialized_types= {'alert_token': 'str', 'created_time': 'str', 'href': 'str', 'status': 'ask_sdk_model.services.reminder_management.status.Status', 'updated_time': 'str', 'version': 'str'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.reminder_started_event_request module
class
ask_sdk_model.services.reminder_management.reminder_started_event_request.
ReminderStartedEventRequest(request_id=None, timestamp=None, locale=None, body=None)
Bases: ask_sdk_model.request.Request

Parameters:
request_id ((optional) str) – Represents the unique identifier for the specific request.
timestamp ((optional) datetime) – Provides the date and time when Alexa sent the request as an ISO 8601 formatted string. Used to verify the request when hosting your skill as a web service.
locale ((optional) str) – A string indicating the user’s locale. For example: en-US. This value is only provided with certain request types.
body ((optional) ask_sdk_model.services.reminder_management.event.Event) –
attribute_map= {'body': 'body', 'locale': 'locale', 'object_type': 'type', 'request_id': 'requestId', 'timestamp': 'timestamp'}
deserialized_types= {'body': 'ask_sdk_model.services.reminder_management.event.Event', 'locale': 'str', 'object_type': 'str', 'request_id': 'str', 'timestamp': 'datetime'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.reminder_status_changed_event_request module
class
ask_sdk_model.services.reminder_management.reminder_status_changed_event_request.
ReminderStatusChangedEventRequest(request_id=None, timestamp=None, locale=None, body=None)
Bases: ask_sdk_model.request.Request

Parameters:
request_id ((optional) str) – Represents the unique identifier for the specific request.
timestamp ((optional) datetime) – Provides the date and time when Alexa sent the request as an ISO 8601 formatted string. Used to verify the request when hosting your skill as a web service.
locale ((optional) str) – A string indicating the user’s locale. For example: en-US. This value is only provided with certain request types.
body ((optional) ask_sdk_model.services.reminder_management.event.Event) –
attribute_map= {'body': 'body', 'locale': 'locale', 'object_type': 'type', 'request_id': 'requestId', 'timestamp': 'timestamp'}
deserialized_types= {'body': 'ask_sdk_model.services.reminder_management.event.Event', 'locale': 'str', 'object_type': 'str', 'request_id': 'str', 'timestamp': 'datetime'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.reminder_updated_event_request module
class
ask_sdk_model.services.reminder_management.reminder_updated_event_request.
ReminderUpdatedEventRequest(request_id=None, timestamp=None, locale=None, body=None)
Bases: ask_sdk_model.request.Request

Parameters:
request_id ((optional) str) – Represents the unique identifier for the specific request.
timestamp ((optional) datetime) – Provides the date and time when Alexa sent the request as an ISO 8601 formatted string. Used to verify the request when hosting your skill as a web service.
locale ((optional) str) – A string indicating the user’s locale. For example: en-US. This value is only provided with certain request types.
body ((optional) ask_sdk_model.services.reminder_management.event.Event) –
attribute_map= {'body': 'body', 'locale': 'locale', 'object_type': 'type', 'request_id': 'requestId', 'timestamp': 'timestamp'}
deserialized_types= {'body': 'ask_sdk_model.services.reminder_management.event.Event', 'locale': 'str', 'object_type': 'str', 'request_id': 'str', 'timestamp': 'datetime'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.spoken_text module
class
ask_sdk_model.services.reminder_management.spoken_text.
SpokenText(locale=None, ssml=None, text=None)
Bases: object

Parameters:
locale ((optional) str) – The locale in which the spoken text is rendered. e.g. en-US
ssml ((optional) str) – Spoken text in SSML format.
text ((optional) str) – Spoken text in plain text format.
attribute_map= {'locale': 'locale', 'ssml': 'ssml', 'text': 'text'}
deserialized_types= {'locale': 'str', 'ssml': 'str', 'text': 'str'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.status module
class
ask_sdk_model.services.reminder_management.status.
Status
Bases: enum.Enum

Status of reminder

Allowed enum values: [ON, COMPLETED]

COMPLETED= 'COMPLETED'
ON= 'ON'
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.trigger module
class
ask_sdk_model.services.reminder_management.trigger.
Trigger(object_type=None, scheduled_time=None, offset_in_seconds=None, time_zone_id=None, recurrence=None)
Bases: object

Trigger information for Reminder

Parameters:
object_type ((optional) ask_sdk_model.services.reminder_management.trigger_type.TriggerType) –
scheduled_time ((optional) datetime) – Valid ISO 8601 format - Intended trigger time
offset_in_seconds ((optional) int) – If reminder is set using relative time, use this field to specify the time after which reminder ll ring (in seconds)
time_zone_id ((optional) str) – Intended reminder's timezone
recurrence ((optional) ask_sdk_model.services.reminder_management.recurrence.Recurrence) –
attribute_map= {'object_type': 'type', 'offset_in_seconds': 'offsetInSeconds', 'recurrence': 'recurrence', 'scheduled_time': 'scheduledTime', 'time_zone_id': 'timeZoneId'}
deserialized_types= {'object_type': 'ask_sdk_model.services.reminder_management.trigger_type.TriggerType', 'offset_in_seconds': 'int', 'recurrence': 'ask_sdk_model.services.reminder_management.recurrence.Recurrence', 'scheduled_time': 'datetime', 'time_zone_id': 'str'}
supports_multiple_types= False
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model

ask_sdk_model.services.reminder_management.trigger_type module
class
ask_sdk_model.services.reminder_management.trigger_type.
TriggerType
Bases: enum.Enum

Type of reminder - Absolute / Relative

Allowed enum values: [SCHEDULED_ABSOLUTE, SCHEDULED_RELATIVE]

SCHEDULED_ABSOLUTE= 'SCHEDULED_ABSOLUTE'
SCHEDULED_RELATIVE= 'SCHEDULED_RELATIVE'
to_dict()
Returns the model properties as a dict

to_str()
Returns the string representation of the model
```
