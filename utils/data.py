import cv2
import time
import random
import os
import csv
from jetbot import Robot, Camera  # [Changed] Import Camera
from SCSCtrl import TTLServo

# ==========================================
# 1. Configuration Variables
# ==========================================
robot = Robot()

# [Camera Setup]
# Using Jetbot Camera class as requested
# 300x300 is standard for Jetbot models (like ResNet)
camera = Camera.instance(width=300, height=300) 

MOTOR_SPEED = 0.3     # 0.4 means 40% speed
MAX_DURATION = 0.4    # Max rotation duration
MIN_DURATION = 0.1    # Min rotation duration
NUM_SAMPLES = 100     # Number of samples
SAVE_DIR = "dataset_full4"
CSV_FILE = "body_angle_data_full4.csv"

# ==========================================
# 2. Initialization
# ==========================================
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# Wait for camera to start up
print("Waiting for camera to initialize...")
time.sleep(2.0)

# Write CSV Header
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["filename", "direction", "duration", "motor_speed"])

# ==========================================
# 3. Define Motor Control Functions
# ==========================================
def stop_robot():
    robot.stop()

def turn_robot(direction, duration):
    """
    direction: 1 (Right Turn), -1 (Left Turn)
    duration: movement time (seconds)
    """
    if direction == 1:
        # Right Turn
        robot.set_motors(MOTOR_SPEED, -MOTOR_SPEED)
    else:
        # Left Turn
        robot.set_motors(-MOTOR_SPEED, MOTOR_SPEED)
    
    time.sleep(duration)
    stop_robot()

# ==========================================
# 4. Data Collection Loop
# ==========================================
print("Start collecting {} samples...".format(NUM_SAMPLES))

try:
    TTLServo.servoAngleCtrl(1, 3, 1, 500)
    TTLServo.servoAngleCtrl(2, -5, 1, 500)
    TTLServo.servoAngleCtrl(3, 0, 1, 500)
    TTLServo.servoAngleCtrl(4, 0, 1, 150)
    TTLServo.servoAngleCtrl(5, 30, 1, 150)

    for i in range(NUM_SAMPLES):
        # 1. Determine random action
        rand_dir = random.choice([1, -1])
        rand_dur = random.uniform(MIN_DURATION, MAX_DURATION)
        
        # 2. Rotate Robot
        turn_robot(rand_dir, rand_dur)
        
        # 3. Wait for vibration
        time.sleep(0.5)
        
        # 4. Capture Image from Jetbot Camera
        # camera.value holds the current frame as a numpy array
        frame = camera.value
        
        if frame is None:
            print("Frame error (None), skipping...")
        else:
            # 5. Save Image
            direction_str = 'R' if rand_dir == 1 else 'L'
            filename = "body_{:04d}_{}_{:.2f}s.jpg".format(i, direction_str, rand_dur)
            
            filepath = os.path.join(SAVE_DIR, filename)
            cv2.imwrite(filepath, frame)
            
            # 6. Save Label
            with open(CSV_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([filename, rand_dir, rand_dur, MOTOR_SPEED])
            
            print("[{}/{}] Saved: {}".format(i+1, NUM_SAMPLES, filename))

        # 7. Return to Origin
        turn_robot(-rand_dir, rand_dur)
        
        # Wait before next loop
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nInterrupted! Stopping motors.")

finally:
    stop_robot()
    # Jetbot Camera usually doesn't need explicit release like cv2, 
    # but stopping the camera allows other apps to use it.
    camera.stop()
    print("Done.")