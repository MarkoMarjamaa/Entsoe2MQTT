import json
import paho.mqtt.client as mqtt
from entsoe import EntsoePandasClient
from datetime import datetime, timedelta
import pytz
import pandas as pd
import time

# Set up your API key and MQTT broker details
API_KEY = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'  # Replace with your ENTSO-E API key
MQTT_BROKER = 'homeautomation'  # Replace with your broker address
MQTT_PORT = 1883
MQTT_TOPIC = 'Entsoe2MQTT/sensor/ElectricityPrice'
MQTT_KEEP_ALIVE_INTERVAL = 60  # seconds
Country='10YFI-1--------U' 
now = datetime.now(pytz.timezone('Europe/Helsinki')) 

last_fetched = False  # Default value

def on_message(client, userdata, msg):
	global last_fetched
	try:
		payload = json.loads(msg.payload.decode('utf-8'))
		raw_tomorrow = payload.get("raw_tomorrow", [])
		if isinstance(raw_tomorrow, list):
			last_fetched = (len(raw_tomorrow)>10)
	except json.JSONDecodeError:
		print("Error decoding JSON message.")
		
# Format times for JSON
def print_time(time):
    strTime = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    return (strTime[:22]+":"+strTime[-2:])

def format_prices(prices):
    
    raw_list = []
    for index, value in prices.items():
        value_dict = {
            "start": print_time(index),
            "end": print_time(index+ timedelta(hours=1)),
            "value": value/10
            } 
        raw_list.append(value_dict)
    
    return raw_list

# Create the entsoe client with your API key
client = EntsoePandasClient(api_key=API_KEY)

# Create MQTT client instance
mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message

# Connect to the MQTT broker
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEP_ALIVE_INTERVAL)

# Get the earlier message if found. 
mqtt_client.subscribe(MQTT_TOPIC)
mqtt_client.loop_start()
time.sleep(1)
mqtt_client.loop_stop()
mqtt_client.unsubscribe(MQTT_TOPIC)

# If tomorrow data has not been successfully fetched yet, try
if ( not last_fetched ):
	today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
	
	# Get prices for today
	prices_today = client.query_day_ahead_prices(
		country_code= Country,  # Example: Germany
		start=pd.to_datetime(today_start),
		end=pd.to_datetime(today_start + timedelta(days=1)),
		resolution = '60min'
		)

	# Get prices for tomorrow
	prices_tomorrow = client.query_day_ahead_prices(
		country_code= Country,
		start=pd.to_datetime(today_start + timedelta(days=1)),
		end=pd.to_datetime(today_start + timedelta(days=2)),
		resolution = '60min'
	)

	# Create the payload in the specified structure
	message = {
			"state": ('ok' if (len(prices_tomorrow)>10) else 'error'),
			"today": prices_today.tolist(),
			"tomorrow": prices_tomorrow.tolist(),
			"raw_today": format_prices(prices_today),
			"raw_tomorrow": format_prices(prices_tomorrow)
	}

	#print(message)
	mqtt_client.publish(MQTT_TOPIC, json.dumps(message, indent=4), retain=True)

mqtt_client.disconnect()
