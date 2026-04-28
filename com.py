import paho.mqtt.client as mqtt
import json
import time
from pipuck.pipuck import PiPuck

# Define variables and callbacks
Broker = "192.168.178.43"  # Replace with your broker address
Port = 1883 # standard MQTT port
position = None
positions = {} # Dictionary to store positions of all robots

def get_position(robot_id, data):
    position = data.get(robot_id, {}).get('position', None)
    return position

def get_distance(pos1, pos2):
    if pos1 is None or pos2 is None:
        return float('inf')  # Return infinity if either position is None
    return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

# function to handle connection
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("robot_pos/all")

# function to handle incoming messages
def on_message(client, userdata, msg):
    global position
    global positions
    try:
        data = json.loads(msg.payload.decode())
        position = get_position("38", data)
        positions = data
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
pipuck.epuck.set_motor_speeds(0,-0)

for _ in range(1000):
    if(position is not None):
        print(f"Current position: {position}")
    if(positions):
        for robot_id, info in positions.items():
            print(f"Position for robot {robot_id}: {info.get('position')}")
            print(f"Distance to robot {robot_id}: {get_distance(position, info.get('position'))}")
    time.sleep(1)
	
    
# Stop the MQTT client loop
pipuck.epuck.set_motor_speeds(0,0)
client.loop_stop()  
