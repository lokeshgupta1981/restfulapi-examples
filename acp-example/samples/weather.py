import requests


def current_temperature(city):
    response = requests.get(f"https://api.example.com/weather?city={city}")
    return response.json()["temperature"]


def forecast(city, days):
    response = requests.get(f"https://api.example.com/forecast?city={city}&days={days}")
    return response.json()["days"]
