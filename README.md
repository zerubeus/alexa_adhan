# Alexa Adhan

<p align="center">
  <img src="skill-package/assets/en-US_largeIcon.png" alt="Alexa Adhan" width="512">
</p>

## Project Functional Description

Alexa Adhan is an Alexa skill that provides prayer call notifications for Muslims. Users can ask for the prayer times of the day and set notifications for each prayer time. The skill will play the Adhan sound when it's time for prayer.

## Project Technical Description

The Alexa Adhan skill is built using the Alexa Skills Kit (ASK) and AWS Lambda. The skill uses the Aladhan API to fetch prayer times based on the user's location. The skill also uses the Alexa Reminders API to set notifications for prayer times. The project is structured with a Lambda function that handles the skill's logic and a set of services for fetching prayer times and managing geolocation.

## Dependency Management

This project uses Poetry for dependency management. To install dependencies, run `poetry install`. To add a new dependency, run `poetry add <dependency-name>`.

## Supported Languages

The Alexa Adhan skill is available in:

- English (EN)
- French (FR)

## Todo List

- [x] Intent to get prayer times for today
- [x] Intent to set reminder for every prayer time
- [ ] Intent to get next prayer time
- [ ] Intent to set an audio (Adhan) notification for every prayer (currently not supported by Alexa reminders)
- [ ] Intent to delete all reminders
