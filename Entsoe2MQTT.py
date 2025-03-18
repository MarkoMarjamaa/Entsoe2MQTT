import json
import paho.mqtt.client as mqtt
from entsoe import EntsoePandasClient
from datetime import datetime, timedelta
import pytz
import pandas as pd

# Set up your API key and MQTT broker details
API_KEY = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'  # Replace with your ENTSO-E API key
MQTT_BROKER = 'homeautomation'  # Replace with your broker address
MQTT_PORT = 1883
MQTT_TOPIC = 'Entsoe2MQTT/sensor/ElectricityPrice'
MQTT_KEEP_ALIVE_INTERVAL = 60  # seconds
Country='10YFI-1--------U' 
now = datetime.now(pytz.timezone('Europe/Helsinki')) 

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

# Connect to the MQTT broker
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEP_ALIVE_INTERVAL)

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
		"state": 'ok',
		"today": prices_today.tolist(),
		"tomorrow": prices_tomorrow.tolist(),
		"raw_today": format_prices(prices_today),
		"raw_tomorrow": format_prices(prices_tomorrow)
}

#print(message)
mqtt_client.publish(MQTT_TOPIC, json.dumps(message, indent=4), retain=True)

mqtt_client.disconnect()
