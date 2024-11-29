import json
from adhan.app import lambda_handler


def test_get_prayer_times():
    with open("tests/events/get_prayer_times.json") as f:
        event = json.load(f)

    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    test_get_prayer_times()
