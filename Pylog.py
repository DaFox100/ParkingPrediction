#sources: https://stackoverflow.com/questions/2047814/is-it-possible-to-store-python-class-objects-in-sqlite
#       : https://github.com/edgargutgzz/sanpedro_trafficdata
import requests
import urllib3
import sqlite3
import config #import config file with api key
import time
import threading
#import googlemaps

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def Create_logger():
    engine = create_engine('sqlite:///log.db')
    Base = declarative_base()
    # gmaps = googlemaps.Client(key = config.api_key)
    use_gmaps_api = False

    class datapoints(Base):
        timestamp = Column(DateTime, primary_key=True)
        South_status = Column(Float)
        South_Traffic_density = Column(Float)
        West_status = Column(Float)
        West_Traffic_density = Column(Float)
        North_status = Column(Float)
        North_Traffic_density = Column(Float)
        SouthCampus_status = Column(Float)
        SouthCampus_Traffic_density = Column(Float)

        __tablename__ = 'datapoints'
        def __init__(self, status):
            timestamp = datetime.now()

    # Function to parse the page string into a datapoint class 
    def parse_page(page):
        place = 0
        output = ["","","",""]
        for i in range (4):
            place = page.text.find("garage__fullness",place) + 18
            while(page.text[place] != '<'):
                if(page.text[place] != ' ' and page.text[place] != '%'):
                    output[i] += page.text[place]
                place = place+1
            if (output[i] == "Full"):
                output[i] = 100
            # print(output[i])
        #convert the outputs from strings to ints 
        try:
            return int(output[0]),int(output[1]),int(output[2]),int(output[3])
        except:
            print("Failed HTML Parsing")
            print("Outputs given as" + str(output[0])+ str(output[1]) + str(output[2]) + str(output[3]))
            return (-1,-1,-1,-1)



    # SQL stuff I coppied from stackoverflow
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    chord_matrix_south = [('37.331625582953414,-121.87854580364586 '), # start 
                        ('37.334487150429325,-121.87647925737306')]  # end
    chord_matrix_north = [('37.33937718837858, -121.87867808610903'),  # start 
                        ('37.33862154592525, -121.88059524423632')]  # end
    chord_matrix_west  = [('37.332457789029654,-121.88500484501284'),  # start 
                        ('37.33226916403564, -121.88324302924795')]  # end
    chord_matrix_southcampus = [('37.329669686864655, -121.86879034440456'), # start 
                                ('37.320913786693346, -121.8653592200895')]  # end

    # return the average traffic velocity in from the chordinate pairs given 
    # def get_traffic_density(chord_matrix):
    #     # distance and velocity calculations from https://github.com/edgargutgzz/sanpedro_trafficdata
    #     response = gmaps.distance_matrix(chord_matrix[0],chord_matrix[1], departure_time = "now")
    #     distance = (response['rows'][0]['elements'][0]['distance']['value']/1000)
    #     duration_traffic = (response['rows'][0]['elements'][0]['duration_in_traffic']['value']) / 60
    #     velocity = (distance / duration_traffic) * 60
    #     return velocity


    # get the PAGE request and store it in page
    # we then parse the page, creating a datapoint(s) object, 
    # then adding that object to our log.db file
    URL = "https://sjsuparkingstatus.sjsu.edu/"
    URL2 = "https://sjsuspartans.com/all-sports-schedule?view=grid"
    while (1):
        try:
            page = requests.get(URL, verify=False)
            page.raise_for_status()
        except requests.exceptions.HTTPError as errh: 
            print("HTTP Error") 
            print(errh.args[0])
        if(page.status_code == 200):
            output = parse_page(page)
            datapoint1 = datapoints(output)
            datapoint1.timestamp = datetime.now()
            datapoint1.South_status = output[0]/100
            datapoint1.West_status = output[1]/100
            datapoint1.North_status = output[2]/100
            datapoint1.SouthCampus_status = output[3]/100
            if (datetime.now().hour >= 6 and datetime.now().hour < 21):
                use_gmaps_api = True
                print("Valid API time")
            else:
                use_gmaps_api = False
                print("Invalid API time")
            # datapoint1.South_Traffic_density= get_traffic_density(chord_matrix_south)
            # datapoint1.West_Traffic_density = get_traffic_density(chord_matrix_west)
            # datapoint1.North_Traffic_density = get_traffic_density(chord_matrix_north)
            # datapoint1.SouthCampus_Traffic_density = get_traffic_density(chord_matrix_southcampus)
            
            print(datetime.now())
            print("South:       ", output[0]/100, '|')
            print("West:        ", output[1]/100, '|')
            print("North:       ", output[2]/100, '|')
            print("South campus:", output[3]/100, '|')

            # obj = s.query(datapoints).order_by(datapoints.timestamp.desc()).first()
            # datapoint1.South_Traffic_density= obj.South_Traffic_density
            # datapoint1.West_Traffic_density = obj.West_Traffic_density
            # datapoint1.North_Traffic_density = obj.North_Traffic_density
            # datapoint1.SouthCampus_Traffic_density = obj.South_Traffic_density
            if output[0] == -1 or output[1] == -1 or output[2] == -1 or output[3] == -1:
                time.sleep(60)
            else:
                s.add(datapoint1)
                s.commit()
            if (use_gmaps_api == True):
                time.sleep(600)
            else:
                time.sleep(3600)
        else:
            time.sleep(600)
    #for a in s.query(datapoints):
            #   print(a.timestamp)
thread = threading.Thread(target = Create_logger, args = [])
thread.start()
while (True):
    time.sleep(1)
    if (thread.is_alive() != True):
        print("Thread failure, starting new thread")
        thread = threading.Thread(target = Create_logger, args = [])
        thread.start()
        
