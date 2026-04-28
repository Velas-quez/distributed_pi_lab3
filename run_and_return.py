import paho.mqtt.client as mqtt
import json
import math
import time
from pipuck.pipuck import PiPuck

# Define variables and callbacks
Broker = "192.168.178.43"  # Replace with your broker address
Port = 1883 # standard MQTT port
position = None
angle = None
resulting_force = (0,0) #[magnitude, direction]
positions = {} # Dictionary to store positions of all robots
pipuck = None
self_robot_id = "38" # Unique ID for this robo
arena_w = 2000
arena_h = 1000
max_speed = 1000

# Force constants
max_force = 1000
attraction_strength = 1.0
repulsion_strength = 1.0
wall_repulsion_strength = 1.0
robot_repulsion_strength = 1.0
wall_distance_threshold = (0.02, 0.5)  # Min and max distance for wall repulsion
robot_distance_threshold = (0.02, 0.5)  # Min and max distance for robot repulsion

def get_position(robot_id, data):
    position = data.get(robot_id, {}).get('position', None)
    return position

def get_angle(robot_id, data):
    angle = data.get(robot_id, {}).get('angle', None)
    return angle

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

def distance_to_force(distance, distance_threshold, max_force_value):
    min_threshold, max_threshold = distance_threshold

    if distance >= max_threshold:
        return 0.0
    if distance <= min_threshold:
        return float(max_force_value)

    threshold_range = max_threshold - min_threshold
    if threshold_range <= 0:
        return float(max_force_value)

    normalized_distance = (max_threshold - distance) / threshold_range
    return normalized_distance * max_force_value

def add_wall_forces(current_position, total_force_x, total_force_y):
    x, y = current_position
    wall_distances = (
        ("left", x, (1.0, 0.0)),
        ("right", arena_w - x, (-1.0, 0.0)),
        ("bottom", y, (0.0, 1.0)),
        ("top", arena_h - y, (0.0, -1.0)),
    )

    for wall_name, distance, direction in wall_distances:
        wall_force = distance_to_force(distance, wall_distance_threshold, max_force) * wall_repulsion_strength
        if wall_force > 0:
            total_force_x += direction[0] * wall_force
            total_force_y += direction[1] * wall_force
            print(f"Wall {wall_name} is close! distance={distance:.3f}, force={wall_force:.2f}")

    return total_force_x, total_force_y

def normalize_angle(angle_value):
    return math.atan2(math.sin(angle_value), math.cos(angle_value))

def to_radians(angle_value):
    if angle_value is None:
        return None
    if abs(angle_value) > (2 * math.pi):
        return math.radians(angle_value)
    return angle_value

def clamp_speed(speed_value):
    return max(-max_speed, min(max_speed, speed_value))

def force_to_motor_speeds(current_angle, force_magnitude, force_angle):
    if current_angle is None or force_magnitude <= 0:
        return 0, 0, 0.0

    current_angle = to_radians(current_angle)
    angle_error = normalize_angle(force_angle - current_angle)

    fast_wheel_speed = min(force_magnitude / max_force, 1.0) * max_speed
    turn_factor = abs(angle_error) / math.pi
    slow_wheel_speed = fast_wheel_speed * (1.0 - (2.0 * turn_factor))

    if angle_error > 0:
        left_speed = slow_wheel_speed
        right_speed = fast_wheel_speed
    else:
        left_speed = fast_wheel_speed
        right_speed = slow_wheel_speed

    return clamp_speed(left_speed), clamp_speed(right_speed), angle_error

def handle_robot_topic(data):
    print(f"Mensagem recebida em robot/{self_robot_id}: {data}")
    if pipuck is not None:
        blink_robot_leds(pipuck, times=3, interval=0.05, colour="green")

def handle_robot_positions(data):
    global position
    global angle
    global positions
    position = get_position(self_robot_id, data)
    angle = get_angle(self_robot_id, data)
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
    resulting_force = (0,0)  # Reset forces each loop
    total_force_x = 0.0
    total_force_y = 0.0

    if position is not None:
        total_force_x, total_force_y = add_wall_forces(position, total_force_x, total_force_y)

    if positions and position is not None:
        for robot_id, info in positions.items():
            if robot_id == self_robot_id:
                continue  # Skip self

            other_position = info.get('position')
            distance = get_distance(position, other_position)
            robot_force = distance_to_force(distance, robot_distance_threshold, max_force)

            if robot_force > 0:
                dx = position[0] - other_position[0]
                dy = position[1] - other_position[1]

                if distance > 0:
                    total_force_x += (dx / distance) * robot_force
                    total_force_y += (dy / distance) * robot_force

                print(f"Robot {robot_id} is close! distance={distance:.3f}, force={robot_force:.2f}")
                publish_robot_message(client, robot_id, {"message": f"Hello from robot {self_robot_id}!"})
                print(f"Message sent to robot {robot_id}")

    if position is not None:
        resulting_magnitude = math.hypot(total_force_x, total_force_y)
        resulting_direction = math.atan2(total_force_y, total_force_x) if resulting_magnitude > 0 else 0.0
        resulting_force = (resulting_magnitude, resulting_direction)
        print(f"Resulting force: magnitude={resulting_force[0]:.2f}, direction={resulting_force[1]:.3f}")

        left_speed, right_speed, angle_error = force_to_motor_speeds(angle, resulting_force[0], resulting_force[1])
        pipuck.epuck.set_motor_speeds(left_speed, right_speed)
        print(
            f"Motor speeds: left={left_speed:.2f}, right={right_speed:.2f}, "
            f"angle_error={math.degrees(angle_error):.2f} deg"
        )
    time.sleep(1)
	
    
# Stop the MQTT client loop
pipuck.epuck.set_motor_speeds(0,0)
client.loop_stop()  
