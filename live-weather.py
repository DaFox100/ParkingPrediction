# This script fetches historical weather data from NWS's API
import requests
import csv

latitude = 37.34
longitude = -121.87

# Fetching the metadata URL for the given latitude and longitude
metadata_url = f"https://api.weather.gov/points/{latitude},{longitude}"
response = requests.get(metadata_url)
response.raise_for_status()
forecast_url = response.json()['properties']['forecastHourly']


# Data by hour
forecast = requests.get(forecast_url).json()
hourly_data = forecast['properties']['periods'][:12]

# Creating a CSV file with the data
with open("weather_forecast_sjsu.csv", mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["startTime", "temperature_F", "shortForecast"])

    for period in hourly_data:
        writer.writerow([period['startTime'], period['temperature'], period['shortForecast']])