import torch
import cv2
import time
import threading
import numpy as np
import pathlib
import sys
import os

try:
    from jetbot import Robot, Camera, bgr8_to_jpeg
    from SCSCtrl import TTLServo
except ImportError:
    print("Warning: Jetbot/SCSCtrl libraries not found. Running in mock mode.")
    
    class Robot:
        def stop(self): pass
        def forward(self, x): pass
        def backward(self, x): pass
        def left(self, x): pass
        def right(self, x): pass
    class Camera:
        @staticmethod
        def instance(width, height): return Camera()
        def start(self): pass
        def stop(self): pass
        @property
        def value(self): return np.zeros((300, 300, 3), dtype=np.uint8)
        def observe(self, callback, names): pass
        def unobserve(self, callback, names): pass
    class TTLServo:
        @staticmethod
        def servoAngleCtrl(*args): pass

pathlib.WindowsPath = pathlib.PosixPath

class AGVService:
    def __init__(self):
        self.is_running = False
        self.model = None
        self.robot = None
        self.camera = None
        self.thread = None
        self.status_message = "Initialized"
        
        # 파라미터 설정
        self.conf_threshold = 0.5
        self.iou_match_threshold = 0.7
        self.size_ratio_eps = 0.15
        
        self.move_speed = 0.25
        self.turn_speed = 0.22
        self.move_dt = 0.10
        self.turn_dt = 0.08
        self.move_cooldown = 0.50
        self.grap_cooldown = 2.0
        
        self.last_move_t = 0.0
        self.last_grap_t = 0.0

        self.model_path = os.path.join(os.path.dirname(__file__), "../../utils/best.pt") 
        if not os.path.exists(self.model_path):
             self.model_path = "best.pt"

    def load_model(self):
        if self.model is None:
            print(f"Loading YOLOv5 model from {self.model_path}...")
            try:
                self.model = torch.hub.load(
                    'ultralytics/yolov5:v7.0',
                    'custom',
                    path=self.model_path,
                    force_reload=False
                )
                self.model.to('cuda' if torch.cuda.is_available() else 'cpu')
                self.model.eval()
                self.names = getattr(self.model, "names", {}) or {}
                print("Model loaded successfully.")
            except Exception as e:
                print(f"Failed to load model: {e}")
                self.status_message = f"Model Load Error: {e}"

    def init_hardware(self):
        if self.robot is None:
            self.robot = Robot()
        
        TTLServo.servoAngleCtrl(4, 40, 1, 300)
        TTLServo.servoAngleCtrl(1, 0, 1, 150)
        TTLServo.servoAngleCtrl(2, 0, 1, 150)
        TTLServo.servoAngleCtrl(3, 0, 1, 150)
        TTLServo.servoAngleCtrl(5, 10, 1, 150)

    def start(self):
        if self.is_running:
            return {"status": "Already running"}
        
        self.load_model()
        self.init_hardware()
        
        if self.camera is None:
            self.camera = Camera.instance(width=300, height=300)
        self.camera.start()
        
        self.is_running = True
        self.thread = threading.Thread(target=self._control_loop, daemon=True)
        self.thread.start()
        return {"status": "Started"}

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        
        if self.robot:
            self.robot.stop()
        
        if self.camera:
            self.camera.stop()
            
        self.status_message = "Stopped"
        return {"status": "Stopped"}

    def _control_loop(self):
        print("Control loop started.")
        while self.is_running:
            try:
                image = self.camera.value
                if image is None:
                    time.sleep(0.1)
                    continue

                h, w = image.shape[:2]

                with torch.no_grad():
                    results = self.model(image)

                pred = results.xyxy[0]
                roi = self._get_red_roi_xyxy(h, w)
                roi_cx = (roi[0] + roi[2]) / 2.0
                
                best = None
                if pred is not None and len(pred) > 0:
                    confs = pred[:, 4]
                    keep = confs >= self.conf_threshold
                    if bool(keep.any()):
                        cand = pred[keep]
                        idx = torch.argmax(cand[:, 4])
                        x1, y1, x2, y2, conf, cls = cand[idx].tolist()
                        best = ((int(x1), int(y1), int(x2), int(y2)), float(conf), int(cls))

                now = time.time()
                action = "wait"

                if best is None:
                    self.robot.stop()
                    self.status_message = "No detection"
                
                elif (now - self.last_move_t) < self.move_cooldown:
                    self.robot.stop()
                    self.status_message = "Cooldown"
                
                else:
                    bbox, conf, cls = best
                    bx1, by1, bx2, by2 = bbox
                    
                    iou = self._bbox_iou_xyxy(bbox, roi)
                    bbox_area = max(1, (bx2 - bx1)) * max(1, (by2 - by1))
                    roi_area = max(1, (roi[2] - roi[0])) * max(1, (roi[3] - roi[1]))
                    size_ratio = bbox_area / roi_area
                    bbox_cx = (bx1 + bx2) / 2.0
                    
                    name = self.names.get(cls, str(cls))

                    if iou >= self.iou_match_threshold and (now - self.last_grap_t) > self.grap_cooldown:
                        action = "grap"
                        self.robot.stop()
                        self._grap_action()
                        self.last_grap_t = time.time()
                        self.last_move_t = time.time()
                    
                    elif size_ratio < (1 - self.size_ratio_eps):
                        action = "forward"
                        self._move_forward()
                        self.last_move_t = now
                    
                    elif size_ratio > (1 + self.size_ratio_eps):
                        action = "backward"
                        self._move_backward()
                        self.last_move_t = now
                    
                    else:
                        if bbox_cx > roi_cx:
                            action = "right"
                            self._turn_right()
                        else:
                            action = "left"
                            self._turn_left()
                        self.last_move_t = now
                    
                    self.status_message = f"Tracking {name}: {action} (IoU={iou:.2f})"

            except Exception as e:
                print(f"Error in control loop: {e}")
                time.sleep(1)

            time.sleep(0.01)

    def _get_red_roi_xyxy(self, h, w):
        return (130, h - 140, 170, h - 80)

    def _bbox_iou_xyxy(self, a, b):
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        inter = iw * ih
        area_a = max(0, (ax2 - ax1)) * max(0, (ay2 - ay1))
        area_b = max(0, (bx2 - bx1)) * max(0, (by2 - by1))
        union = area_a + area_b - inter
        return 0.0 if union <= 0 else float(inter / union)

    def _move_forward(self):
        self.robot.forward(self.move_speed)
        time.sleep(self.move_dt)
        self.robot.stop()

    def _move_backward(self):
        self.robot.backward(self.move_speed)
        time.sleep(self.move_dt)
        self.robot.stop()

    def _turn_left(self):
        self.robot.left(self.turn_speed)
        time.sleep(self.turn_dt)
        self.robot.stop()

    def _turn_right(self):
        self.robot.right(self.turn_speed)
        time.sleep(self.turn_dt)
        self.robot.stop()

    def _grap_action(self):
        TTLServo.servoAngleCtrl(5, 60, 1, 150)
        TTLServo.servoAngleCtrl(2, 120, 1, 150)
        TTLServo.servoAngleCtrl(3, 110, 1, 150)
        time.sleep(3.5)
        TTLServo.servoAngleCtrl(4, -20, 1, 150)

