from jetbot import Robot
import time

def move_forward(robot, speed=0.5, duration=1):
    robot.left_motor.value = speed
    robot.right_motor.value = speed
    
    time.sleep(duration)
    robot.stop()

def move_backward(robot, speed=0.5, duration=1):
    robot.left_motor.value = -speed
    robot.right_motor.value = -speed
    
    time.sleep(duration)
    robot.stop()

def turn_left(robot, speed=0.3, duration=2):
    robot.left_motor.value = -speed
    robot.right_motor.value = speed
    
    time.sleep(duration)
    robot.stop()

def turn_right(robot, speed=0.3, duration=2):
    robot.left_motor.value = speed
    robot.right_motor.value = -speed
    
    time.sleep(duration)
    robot.stop()

def stop_robot(robot):
    robot.stop()