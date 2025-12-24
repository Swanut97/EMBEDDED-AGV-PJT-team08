import paho.mqtt.client as mqtt
import json

class MqttWorker:
    def __init__(self):
        # Using Callback API V2 to avoid warnings
        self.client = mqtt.Client(protocol=mqtt.MQTTv311)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.message_callback = None 

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("MQTT Connected successfully")
            # Auto subscribe to control topic upon connection
            client.subscribe("jetbot/status")
        else:
            print(f"Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        # Decode message and trigger callback
        try:
            payload = msg.payload.decode('utf-8')
            print(f"Received: {msg.topic} -> {payload}")
            if self.message_callback:
                self.message_callback(payload)
        except Exception as e:
            print(f"Error decoding message: {e}")

    def connect_broker(self, ip, port=1883):
        try:
            self.client.connect(ip, port, 60)
            self.client.loop_start()  # Start background thread
        except Exception as e:
            print(f"Connection Error: {e}")

    def publish_data(self, topic, data):
        # Can handle both string and dictionary (JSON)
        if isinstance(data, dict):
            payload = json.dumps(data)
        else:
            payload = str(data)
            
        info = self.client.publish(topic, payload)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            print("Failed to publish")

    def set_callback(self, func):
        """Set function to execute when message arrives"""
        self.message_callback = func