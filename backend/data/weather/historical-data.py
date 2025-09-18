import requests
import csv
from collections import defaultdict

NOAA_TOKEN = "NVclwfhaIeNZjsoofcpPpNyxMbUvpekA"

headers = {
    'token': NOAA_TOKEN
}

base_params = {
    'datasetid': 'GHCND',
    'stationid': 'GHCND:USW00023293',
    'startdate': '2024-08-20',
    'enddate': '2025-04-30',
    'limit': 1000,
    'units': 'standard'
}

url = 'https://www.ncei.noaa.gov/cdo-web/api/v2/data'

all_results = []
offset = 1  # NOAA uses 1-based offset

print("Fetching NOAA data in pages...")

while True:
    params = base_params.copy()
    params['offset'] = offset

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Request failed at offset {offset}: {response.status_code}")
        break

    data = response.json()
    results = data.get('results', [])

    if not results:
        break

    all_results.extend(results)
    print(f"Retrieved {len(results)} records (offset {offset})")

    if len(results) < 1000:
        break  # last page reached

    offset += 1000

# data by date
weather_by_date = defaultdict(dict)

for item in all_results:
    date = item['date'][:10]
    datatype = item['datatype']
    value = item['value']
    weather_by_date[date][datatype] = value

# csv similar to the live-weather
with open('historical_weather.csv', mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["startTime", "temperature_F", "shortForecast"])

    for date, values in sorted(weather_by_date.items()):
        tmin = values.get("TMIN")
        tmax = values.get("TMAX")
        prcp = values.get("PRCP", 0)

        if tmin is not None and tmax is not None:
            avg_temp = round((tmin + tmax) / 2)
        else:
            avg_temp = tmax or tmin or ''

        if prcp and prcp > 0:
            forecast = "Rain"
        elif avg_temp == '':
            forecast = "Unknown"
        elif avg_temp < 50:
            forecast = "Cold"
        elif avg_temp < 65:
            forecast = "Partly Cloudy"
        else:
            forecast = "Clear"

        writer.writerow([f"{date}T12:00:00", avg_temp, forecast])

print("NOAA full data saved as 'historical_weather.csv'")
