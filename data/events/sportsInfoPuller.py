import csv
import time as t
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser
import os
from pathlib import Path

# Pre-defined sport encoding mapping (extracted from sjsu_home_games.csv)
sport_mapping = {
    "Women's Basketball": 1,
    "Men's Basketball": 2,
    "Women's Tennis": 3,
    "Women's Gymnastics": 4,
    "Women's Swimming and Diving": 5,
    "Softball": 6,
    "Baseball": 7,
    "Women's Golf": 8,
    "Women's Water Polo": 9,
    "Men's Water Polo": 10,
    "Women's Soccer": 11,
    "Football": 12,
    "Men's Golf": 13,
    "Men's Soccer": 14,
    "Women's Volleyball": 15,
    "Women's Beach Volleyball": 16,
    "Track and Field": 17,
}

# Get the current year and month
current_year = datetime.now().year
current_month = datetime.now().month

# Generate years and months dynamically
years = [str(year) for year in range(current_year-1, current_year + 1)]
months = [f"{month:02}" for month in range(1, 13)]

# Set up Selenium with headless Firefox
options = Options()
options.headless = True

# Launch browser
driver = webdriver.Firefox(options=options)

# Update the file path to save the CSV in the records folder relative to the events directory
output_csv_path = f"{Path(__file__).parent.parent}/records/sjsu_home_games.csv"

# Prepare CSV file with two columns: Time and Sport.
with open(output_csv_path, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Time", "Sport"])
    for year in years:
        for month in months:
            if int(year) == current_year and int(month) == current_month:
                # Scrape both past and upcoming events for the current month
                urls = [
                    f'https://sjsuspartans.com/all-sports-schedule?view=calendar&month={year}-{month}&event-time=past&type=home',
                    f'https://sjsuspartans.com/all-sports-schedule?view=calendar&month={year}-{month}&event-time=upcoming&type=home'
                ]
            else:
                # Scrape only past or upcoming events based on the month
                urls = [
                    f'https://sjsuspartans.com/all-sports-schedule?view=calendar&month={year}-{month}&event-time=past&type=home'
                    if int(year) < current_year or (int(year) == current_year and int(month) < current_month)
                    else f'https://sjsuspartans.com/all-sports-schedule?view=calendar&month={year}-{month}&event-time=upcoming&type=home'
                ]

            for url in urls:
                try:
                    driver.get(url)
                    print(f"🔄 Scraping {year}-{month} from {url}... Waiting for JavaScript to load...")
                    t.sleep(5)  # Allow content to load

                    # Get the rendered HTML
                    html = driver.page_source
                    soup = BeautifulSoup(html, 'html.parser')

                    events = soup.find_all(class_='schedule-calendar-day')

                    for event in events:
                        day_num_elem = event.find(class_='schedule-calendar-day__number')
                        day = day_num_elem.text.strip() if day_num_elem else ""

                        button_elems = event.find_all(class_="schedule-calendar-event__button")
                        for button_elem in button_elems:
                            time_and_sport = button_elem.text.strip() if button_elem else ""

                            if day and time_and_sport:
                                # Extract time and sport from the button text
                                time, sport = time_and_sport.split(" - ", 1) if " - " in time_and_sport else ("", time_and_sport)
                                if (time == "All Day ") or (time == "TBA "):
                                    date_str = f"{year}-{month}-{day} 8:00 AM PST"
                                else:
                                    date_str = f"{year}-{month}-{day} {time}"
                                date_obj = parser.parse(date_str)
                                sport_code = sport_mapping.get(sport.strip(), "0")

                                # Format the date without timezone
                                formatted_date = date_obj.strftime("%Y-%m-%dT%H:%M:%S")

                                writer.writerow([formatted_date, sport_code])

                except Exception as e:
                    print(f"❌ Error scraping {year}-{month} from {url}: {e}")

# Close the browser
driver.quit()