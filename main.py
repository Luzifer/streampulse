import logging
import os
import sys

from bluepy import btle
from bluepy.btle import AssignedNumbers, BTLEDisconnectError
import paho.mqtt.client as mqtt


class TransformDelegate(btle.DefaultDelegate):
    def __init__(self, handle, callback, transform):
        btle.DefaultDelegate.__init__(self)
        self.handle = handle
        self.callback = callback
        self.transform = transform

    def handleNotification(self, cHandle, data):
        if cHandle != self.handle:
            return

        self.callback(self.transform(data))


class StreamPulse:
    def __init__(self, **kwargs):
        self.address = kwargs['address']
        self.topic_prefix = kwargs['mqtt_prefix'] if 'mqtt_prefix' in kwargs else 'streampulse'

        if 'mqtt_host' in kwargs and kwargs['mqtt_host'] != '':
            self.mqtt = mqtt.Client()
            if 'mqtt_user' in kwargs:
                self.mqtt.username_pw_set(
                    kwargs['mqtt_user'],
                    kwargs['mqtt_pass'],
                )
            self.mqtt.connect(
                kwargs['mqtt_host'],
                kwargs['mqtt_port'] if 'mqtt_port' in kwargs else 1883,
            )
        else:
            self.mqtt = None

    def run(self):
        if self.mqtt is not None:
            self.mqtt.loop_start()

        while True:
            dev = None

            try:
                logging.debug("Connecting...")
                dev = btle.Peripheral(self.address)
                self.send_mqtt('connected', 'true', True)

                self.add_subscription(
                    dev,
                    AssignedNumbers.batteryService,
                    AssignedNumbers.batteryLevel,
                    self.handle_battery,
                    lambda data: int(data[0]),
                    True,
                )

                self.add_subscription(
                    dev,
                    AssignedNumbers.heartRate,
                    AssignedNumbers.heart_rate_measurement,
                    self.handle_heart_rate,
                    lambda data: int(data[1]),
                    False,
                )

                while True:
                    if dev.waitForNotifications(1.0):
                        continue

            except BTLEDisconnectError:
                logging.error("Device connection error")

            except KeyboardInterrupt:
                if dev is not None:
                    dev.disconnect()
                break

            finally:
                self.send_mqtt('connected', 'false', True)
                if dev is not None:
                    dev.disconnect()

        if self.mqtt is not None:
            self.mqtt.loop_stop()
        return 0

    def add_subscription(self, dev, svc_uuid, char_uuid, callback, transform, initial_read=False):
        svc = dev.getServiceByUUID(svc_uuid)
        char = svc.getCharacteristics(char_uuid)[0]
        desc = char.getDescriptors(
            AssignedNumbers.client_characteristic_configuration,
        )

        dev.setDelegate(TransformDelegate(
            char.getHandle(),
            callback,
            transform,
        ))
        dev.writeCharacteristic(desc[0].handle, b"\x01\x00")

        if initial_read:
            callback(transform(char.read()))

    def get_full_topic(self, topic):
        return '/'.join([self.topic_prefix, topic])

    def handle_battery(self, level):
        logging.debug("Battery Level: {}".format(level))
        self.send_mqtt('battery', level, True)

    def handle_heart_rate(self, rate):
        logging.debug("Heart Rate: {}".format(rate))
        self.send_mqtt('heart_rate', rate, False)

    def send_mqtt(self, topic, payload, retain=False):
        if self.mqtt is None:
            return

        self.mqtt.publish(
            self.get_full_topic(topic),
            payload=payload,
            qos=1,
            retain=retain,
        )


if __name__ == '__main__':
    logging.basicConfig(
        format='[%(asctime)s][%(levelname)s] %(message)s',
        level=logging.DEBUG,
    )

    pulse = StreamPulse(
        address=os.environ['DEVICE'] if 'DEVICE' in os.environ else 'a0:9e:1a:70:54:5e',
        mqtt_host=os.environ['MQTT_HOST'] if 'MQTT_HOST' in os.environ else '',
        mqtt_pass=os.environ['MQTT_PASS'] if 'MQTT_PASS' in os.environ else '',
        mqtt_port=int(os.environ['MQTT_PORT']
                      ) if 'MQTT_PORT' in os.environ else 1883,
        mqtt_prefix=os.environ['MQTT_PREFIX'] if 'MQTT_PREFIX' in os.environ else 'streampulse',
        mqtt_user=os.environ['MQTT_USER'] if 'MQTT_USER' in os.environ else '',
    )

    sys.exit(pulse.run())
