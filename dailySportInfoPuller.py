import csv
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Setup headless Chrome options (uncomment headless for silent mode)
options = Options()
# options.headless = True

# Launch browser
driver = webdriver.Chrome(options=options)

# Get today's date
today = datetime.now()
year = today.strftime("%Y")
month = today.strftime("%m")
day = today.strftime("%d")

# Prepare CSV file
with open("sjsu_home_games_today.csv", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Date", "Time", "Sport"])  # CSV Header

    try:
        url = f'https://sjsuspartans.com/all-sports-schedule?view=calendar&month={year}-{month}&event-time=past'
        driver.get(url)

        print(f"🔄 Scraping {year}-{month}-{day}... Waiting for JavaScript to load...")
        time.sleep(10)  # Allow content to load

        events = driver.find_elements(By.CLASS_NAME, 'schedule-calendar-day')

        found_any_event = False  # Track if any event is found for today

        for event in events:
            try:
                day_num_elem = event.find_element(By.CLASS_NAME, 'schedule-calendar-day__number')
                event_day = day_num_elem.text.strip().zfill(2)
                if event_day != day:
                    continue  # Skip days that are not today

                date_str = f"{month}/{day}/{year}"
                home_events = event.find_elements(By.CLASS_NAME, 'schedule-calendar-event--home')

                if home_events:
                    found_any_event = True
                    for home_event in home_events:
                        button = home_event.find_element(By.CLASS_NAME, 'schedule-calendar-event__button')
                        full_text = button.text.strip()

                        parts = full_text.split("–")
                        time_str = parts[0].strip() if len(parts) > 0 else ""
                        sport = parts[1].strip() if len(parts) > 1 else ""

                        writer.writerow([date_str, time_str, sport])
                        print(f"✅ Found: {date_str}, {time_str}, {sport}")

            except Exception as inner_e:
                print(f"⚠️ Error processing an event: {inner_e}")

        # If no events found for today, write null row
        if not found_any_event:
            date_str = f"{month}/{day}/{year}"
            writer.writerow([date_str, "null", "null"])
            print(f"ℹ️ No events found. Wrote null entry for {date_str}")

    except Exception as e:
        print(f"❌ Error fetching events: {e}")

# Close browser
driver.quit()
print("🏁 Today's home games saved to 'sjsu_home_games_today.csv'")
