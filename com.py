import paho.mqtt.client as mqtt
import json
import time
from pipuck.pipuck import PiPuck

# Define variables and callbacks
Broker = "192.168.178.43"  # Replace with your broker address
Port = 1883 # standard MQTT port
position = None
positions = {} # Dictionary to store positions of all robots
pipuck = None
self_robot_id = "38" # Unique ID for this robo

def get_position(robot_id, data):
    position = data.get(robot_id, {}).get('position', None)
    return position

def publish_robot_message(client, robot_id, message):
    topic = f"robot/{robot_id}"
    payload = message if isinstance(message, str) else json.dumps(message)
    result = client.publish(topic, payload)
    return result

def blink_robot_leds(pipuck, times=3, interval=0.3, colour="white"):
    for _ in range(times):
        pipuck.set_leds_colour(colour)
        time.sleep(interval)
        pipuck.set_leds_colour("off")
        time.sleep(interval)

def get_distance(pos1, pos2):
    if pos1 is None or pos2 is None:
        return float('inf')  # Return infinity if either position is None
    return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

def handle_robot_topic(data):
    print(f"Mensagem recebida em robot/{self_robot_id}: {data}")
    if pipuck is not None:
        blink_robot_leds(pipuck, times=3, interval=0.05, colour="green")

def handle_robot_positions(data):
    global position
    global positions
    position = get_position(self_robot_id, data)
    positions = data

# function to handle connection
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("robot_pos/all")
    client.subscribe(f"robot/{self_robot_id}")

# function to handle incoming messages
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        print(f'invalid json: {msg.payload}')
        return

    if msg.topic == f"robot/{self_robot_id}":
        handle_robot_topic(data)
    elif msg.topic == "robot_pos/all":
        handle_robot_positions(data)
    else:
        print(f"Unhandled topic {msg.topic}: {data}")

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
publish_robot_message(client, self_robot_id, {"status": "online"})
blink_robot_leds(pipuck, times=2, interval=0.2)

for _ in range(1000):
    if(position is not None):
        print(f"Current position: {position}")
    if(positions):
        for robot_id, info in positions.items():
            if robot_id == self_robot_id:
                continue  # Skip self
            distance = get_distance(position, info.get('position'))
            if distance <= 0.5:
                print(f"Robot {robot_id} is close!")
                publish_robot_message(client, robot_id, {"message": f"Hello from robot {self_robot_id}!"})
                print(f"Message sent to robot {robot_id}")
    time.sleep(1)
	
    
# Stop the MQTT client loop
pipuck.epuck.set_motor_speeds(0,0)
client.loop_stop()  
