import paho.mqtt.client as mqtt
import json
import time
from pipuck.pipuck import PiPuck
import random


# Define variables and callbacks
Broker = "192.168.178.43"  # Replace with your broker address
Port = 1883 # standard MQTT port

def positions(data, robot_id):
    
    robot= data[robot_id]
    x= robot['position'][0]
    y= robot['position'][1]
    ang= robot['angle']
    return x,y,ang
    

# function to handle connection
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("robot_pos/all")

# function to handle incoming messages
def on_message(client, userdata, msg):
    global x,y,ang
    try:
        data = json.loads(msg.payload.decode())
        print(data)
        x, y, ang = positions(data, '38')
    except json.JSONDecodeError:
        print(f'invalid json: {msg.payload}')

# Initialize MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(Broker, Port, 60)

client.loop_start() # Start listening loop in separate thread

# Initialize the PiPuck
pipuck = PiPuck(epuck_version=2)

# Set the robot's speed, e.g. with
pipuck.epuck.set_motor_speeds(1000,-1000)


for _ in range(1000):
    # TODO: Do your stuff here
    if(x>=1.9 or y>=0.9):
        pipuck.epuck.set_motor_speeds(1000,-1000)
        time.sleep(2)
    pipuck.epuck.set_motor_speeds(random.randrange(-1000,1000),random.randrange(-1000,1000))
    time.sleep(random.randrange(0,3))
    
	
    
# Stop the MQTT client loop
pipuck.epuck.set_motor_speeds(0,0)
client.loop_stop()  
