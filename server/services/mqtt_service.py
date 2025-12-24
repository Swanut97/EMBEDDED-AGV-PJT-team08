import json
import paho.mqtt.client as mqtt

class MQTTService:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.broker_ip = "127.0.0.1"
        self.port = 1883

    def connect(self):
        try:
            self.client.connect(self.broker_ip, self.port, 60)
            self.client.loop_start()
            print(f"✅ MQTT Publisher Ready: {self.broker_ip}")
        except Exception as e:
            print(f"MQTT Connection Failed: {e}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("MQTT Publisher Stopped")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(">> Connected to Broker (Publish Only)")
        else:
            print(f">> Connection Failed code: {reason_code}")

    def publish(self, topic: str, payload: dict[str, str]):
        try:
            message = json.dumps(payload)

            info = self.client.publish(topic, message, qos=1)

            print(f"[SEND] {topic} : {message}")

        except Exception as e:
            print(f"Publish Error: {e}")

    def command(self, topic: str, cmd: str):
        try:
            if cmd != "None":
                payload = {
                    "command": cmd,
                }
                self.publish(topic, payload)
        except Exception as e:
            print(f"Command Error: {e}")
