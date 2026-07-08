import json
import time
import paho.mqtt.client as mqtt
import threading

MQTT_SERVER = "12e17729f9.st1.iotda-device.cn-north-4.myhuaweicloud.com"
MQTT_PORT = 1883
CLIENT_ID = "6a47a1c8cbb0cf6bb96b8ca9_1111_0_0_2026070407"
USERNAME = "6a47a1c8cbb0cf6bb96b8ca9_1111"
PASSWORD = "dace9b2c7cece2adeb6a0b7434b24d9e58659c0fa04b83e9da95015ee7124bf2"
TOPIC = "$oc/devices/6a47a1c8cbb0cf6bb96b8ca9_1111/sys/properties/report"

class HuaweiCloudMQTT:
    def __init__(self):
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=CLIENT_ID,
            protocol=mqtt.MQTTv311
        )
        self.client.username_pw_set(USERNAME, PASSWORD)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.connect(MQTT_SERVER, MQTT_PORT, 60)
        self.client.loop_start()
        self._connected = False
        self._lock = threading.Lock()
        print("华为云MQTT客户端已创建，正在连接...")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self._connected = True
            print("华为云MQTT连接成功")
        else:
            print(f"华为云MQTT连接失败，返回码: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._connected = False
        print("华为云MQTT连接断开")

    def upload(self, temp=25, heart_rate=0, spo2=0, fall=0, person="unknown", step=0):
        payload = {
            "services": [
                {
                    "service_id": "chanpin1",
                    "properties": {
                        "temp": temp,
                        "heart_rate": heart_rate,
                        "spo2": spo2,
                        "fall": fall,
                        "person": person,
                        "step": step
                    }
                }
            ]
        }
        self._publish(payload)

    def upload_simple(self, temp=25, step=0):
        payload = {
            "services": [
                {
                    "service_id": "chanpin1",
                    "properties": {
                        "temp": temp,
                        "step": step
                    }
                }
            ]
        }
        self._publish(payload)

    def _publish(self, payload_dict):
        msg = json.dumps(payload_dict)
        with self._lock:
            if self._connected:
                self.client.publish(TOPIC, msg, qos=1)
                print(f"华为云上传成功: {msg}")
            else:
                print("华为云MQTT未连接，数据未上传")

    def close(self):
        self.client.loop_stop()
        self.client.disconnect()


_huawei_client = None
def get_huawei_client():
    global _huawei_client
    if _huawei_client is None:
        _huawei_client = HuaweiCloudMQTT()
    return _huawei_client
