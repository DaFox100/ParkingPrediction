import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Setup headless Chrome options (uncomment headless for silent mode)
options = Options()
# options.headless = True

# Launch browser
driver = webdriver.Chrome(options=options)

months24 = ['01','02','03','04','05','06','07','08','09','10','11','12']
months25 = ['01','02','03','04']
years = ['2024','2025']

# Prepare CSV file once
with open("sjsu_home_games.csv", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Date", "Time", "Sport"])  # CSV Header

    for year in years:
        if year == '2024':
            months = months24
        else:
            months = months25

        for month in months:
            try:
                url = f'https://sjsuspartans.com/all-sports-schedule?view=calendar&month={year}-{month}&event-time=past'
                driver.get(url)

                print(f"🔄 Scraping {year}-{month}... Waiting for JavaScript to load...")
                time.sleep(10)  # Allow content to load

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

                        parts = full_text.split("–")
                        time_str = parts[0].strip() if len(parts) > 0 else ""
                        sport = parts[1].strip() if len(parts) > 1 else ""

                        writer.writerow([date, time_str, sport])

                print(f"✅ Done: {year}-{month}")

            except Exception as e:
                print(f"❌ Error on {year}-{month}: {e}")

# Close browser
driver.quit()
print("🏁 All home games saved to 'sjsu_home_games.csv'")
