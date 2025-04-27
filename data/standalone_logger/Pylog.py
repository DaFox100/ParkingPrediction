# IMPORTANT: GET THE API KEY FOR MONGODB AND PUT IT IN THE .ENV FILE
# OR REPLACE THE MONGO_URI VARIABLE WITH THE API KEY


#sources: https://stackoverflow.com/questions/2047814/is-it-possible-to-store-python-class-objects-in-sqlite
#       : https://github.com/edgargutgzz/sanpedro_trafficdata
import requests
import urllib3
import time
import threading
import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# MongoDB connection details
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "sjparking"

def create_logger():
    # Initialize MongoDB client
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db["datapoints"]

    # Function to parse the page string into a datapoint
    def parse_page(page):
        place = 0
        output = ["","","",""]
        for i in range(4):
            place = page.text.find("garage__fullness", place) + 18
            while(page.text[place] != '<'):
                if(page.text[place] != ' ' and page.text[place] != '%'):
                    output[i] += page.text[place]
                place = place + 1
            if (output[i] == "Full"):
                output[i] = 100
        try:
            return int(output[0]), int(output[1]), int(output[2]), int(output[3])
        except:
            print("Failed HTML Parsing")
            print("Outputs given as" + str(output[0]) + str(output[1]) + str(output[2]) + str(output[3]))
            return (-1, -1, -1, -1)

    URL = "https://sjsuparkingstatus.sjsu.edu/"
    
    while True:
        try:
            page = requests.get(URL, verify=False)
            page.raise_for_status()
            
            if page.status_code == 200:
                output = parse_page(page)
                
                # Create datapoint document
                datapoint = {
                    "timestamp": datetime.now(),
                    "metadata": "sjparking",
                    "south_status": output[0],
                    "west_status": output[1],
                    "north_status": output[2],
                    "south_campus_status": output[3]
                }
                
                print(datetime.now())
                print("South:       ", output[0], '|')
                print("West:        ", output[1], '|')
                print("North:       ", output[2], '|')
                print("South campus:", output[3], '|')

                if output[0] == -1 or output[1] == -1 or output[2] == -1 or output[3] == -1:
                    time.sleep(60)
                else:
                    collection.insert_one(datapoint)
                    time.sleep(600)  # Sleep for 10 minutes between requests
            else:
                time.sleep(600)
                
        except requests.exceptions.HTTPError as errh:
            print("HTTP Error")
            print(errh.args[0])
            time.sleep(600)
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(600)

# Start the logger in a separate thread
thread = threading.Thread(target=create_logger)
thread.start()

# Monitor the thread and restart if it fails
while True:
    time.sleep(1)
    if not thread.is_alive():
        print("Thread failure, starting new thread")
        thread = threading.Thread(target=create_logger)
        thread.start()
