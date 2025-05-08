import csv
import time
from datetime import datetime
from dateutil import parser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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
}

# Setup headless Chrome options (uncomment headless for silent mode)
options = Options()
# options.headless = True

# Launch browser
driver = webdriver.Chrome(options=options)

months24 = ['01','02','03','04','05','06','07','08','09','10','11','12']
months25 = ['01','02','03','04','05']
years = ['2024','2025']

# Prepare CSV file with two columns: Time and Sport.
with open("sjsu_home_games.csv", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Time", "Sport"])  # CSV Header

    for year in years:
        months = months24 if year == '2024' else months25

        for month in months:
            try:
                url = f'https://sjsuspartans.com/all-sports-schedule?view=calendar&month={year}-{month}&event-time=past'
                driver.get(url)

                print(f"🔄 Scraping {year}-{month}... Waiting for JavaScript to load...")
                time.sleep(3)  # Allow content to load

                events = driver.find_elements(By.CLASS_NAME, 'schedule-calendar-day')

                for event in events:
                    day_num_elem = event.find_element(By.CLASS_NAME, 'schedule-calendar-day__number')
                    day = day_num_elem.text.strip()
                    if not day.isdigit():
                        continue  # Skip non-date entries

                    date = f"{month}/{day}/{year}"
                    home_events = event.find_elements(By.CLASS_NAME, 'schedule-calendar-event--home')

                    for home_event in home_events:
                        button = home_event.find_element(By.CLASS_NAME, 'schedule-calendar-event__button')
                        full_text = button.text.strip()

                        parts = full_text.split("-")
                        time_str = parts[0].strip() if len(parts) > 0 else ""
                        sport = parts[1].strip() if len(parts) > 1 else ""

                        # Convert time_str from 12-hour to datetime
                        if time_str:
                            try:
                                converted_time = parser.parse(time_str)
                            except ValueError:
                                if time_str == "All Day":
                                    continue
                                elif time_str == "TBD":
                                    continue
                        else:
                            converted_time = ""

                        # Combine the date and time into a datetime object and then ISO format string.
                        if isinstance(converted_time, datetime):
                            date_obj = datetime.strptime(date, "%m/%d/%Y")
                            combined_dt = date_obj.replace(hour=converted_time.hour, minute=converted_time.minute, second=converted_time.second)
                            combined_time_str = combined_dt.isoformat()
                        else:
                            combined_time_str = f"{date} {converted_time}"

                        # Use pre-defined mapping; default to 0 if sport is not in the map.
                        sport_code = sport_mapping.get(sport, 0)
                        writer.writerow([combined_time_str, sport_code])

                print(f"✅ Done: {year}-{month}")

            except Exception as e:
                print(f"❌ Error on {year}-{month}: {e}")

# Close browser
driver.quit()
print("🏁 All home games saved to 'sjsu_home_games.csv'")