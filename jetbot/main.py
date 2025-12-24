import asyncio
import time
import json
from jetbot import Robot

# Import custom modules
from mqtt.client import MqttWorker
import control.movement as move
# import control.arm as arm
# import control.camera as cam

robot = None

# 1. Define logic to handle received commands
def process_command(command_str):
    global robot
    
    try:
        # Assuming the message is JSON string
        data = json.loads(command_str)
        cmd = data.get("cmd")
        val = data.get("val", 0.5) # Default speed

        if cmd == "forward":
            move.move_forward(robot, val)
        elif cmd == "backward":
            move.move_backward(robot, val)
        elif cmd == "left":
            move.turn_left(robot, val)
        elif cmd == "right":
            move.turn_right(robot, val)
        elif cmd == "stop":
            move.stop_robot(robot)
#         elif cmd == "grab":
#             arm.grab_object()
        else:
            print(f"Unknown command: {cmd}")

    except json.JSONDecodeError:
        print("Not a JSON message")
    except Exception as e:
        print(f"Error processing command: {e}")


# 2. Setup and Main Loop
def main():
    
    global robot
    robot = Robot()
    
    # Initialize MQTT
    worker = MqttWorker()
    worker.connect_broker("172.20.10.14") 
    
    # Register the command processing function
    worker.set_callback(process_command)

    print("System Ready. Waiting for commands...")

    try:
        while True:
            # Send Status periodically
            status = {"status": "alive", "timestamp": time.time()}
            #worker.publish_data("jetbot/status", status)
            
            time.sleep(2)

#     except asyncio.CancelledError:
#         print("Async loop cancelled")
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        move.stop_robot()

if __name__ == "__main__":
    main()