import csv
import time as t
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser

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
years = [str(year) for year in range(current_year - 2, current_year + 1)]  # Scrape data for the past 2 years and current year
months = [f"{month:02}" for month in range(1, 13)]  # All months from January to December

# Set up Selenium with headless Firefox
options = Options()
options.headless = True

# Launch browser
driver = webdriver.Firefox(options=options)

# Prepare CSV file with two columns: Time and Sport.
with open("sjsu_home_games.csv", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Time", "Sport"])  # CSV Header

    for year in years:
        for month in months:
            # Skip future months in the current year
            if int(year) == current_year and int(month) > current_month:
                continue

            try:
                url = f'https://sjsuspartans.com/all-sports-schedule?view=calendar&month={year}-{month}&event-time=past'
                driver.get(url)

                print(f"🔄 Scraping {year}-{month}... Waiting for JavaScript to load...")
                t.sleep(1)  # Allow content to load

                # Get the rendered HTML
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')

                events = soup.find_all(class_='schedule-calendar-day')

                for event in events:
                    day_num_elem = event.find(class_='schedule-calendar-day__number')
                    day = day_num_elem.text.strip() if day_num_elem else ""

                    button_elem = event.find(class_='schedule-calendar-event__button')
                    time_and_sport = button_elem.text.strip() if button_elem else ""

                    if day and time_and_sport:
                        # Extract time and sport from the button text
                        time, sport = time_and_sport.split(" - ", 1) if " - " in time_and_sport else ("", time_and_sport)
                        if (time == "All Day "):
                            date_str = f"{year}-{month}-{day} 8:00 AM PST"
                        else:
                            date_str = f"{year}-{month}-{day} {time}"
                        date_obj = parser.parse(date_str)
                        sport_code = sport_mapping.get(sport.strip(), "0")

                        # Format the date without timezone
                        formatted_date = date_obj.strftime("%Y-%m-%dT%H:%M:%S")

                        writer.writerow([formatted_date, sport_code])

            except Exception as e:
                print(f"❌ Error scraping {year}-{month}: {e}")

# Close the browser
driver.quit()