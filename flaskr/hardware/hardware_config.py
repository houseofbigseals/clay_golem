import sys
from enum import unique

sys.path.insert(0, "/opt/clay/clay_golem")
from flaskr.hardware.hardware_base import HardwareLamp, HardwareRelay, HardwareSensorOnRelayBoard, HardwareSBA5
from flaskr.hardware.hardware_collection import HardwareCollection
from flask import current_app, g
from typing import Any



def init_hardware(mode="test"):
    """
    """

    print(f"INIT HARDWARE with mode {mode}")
    # if mode == "test":
    if mode == "production":
        lamp_2_ip = "10.10.0.14"
        relay_5_ip = "10.10.0.18"
        relay_1_ip = "10.10.0.5"
        relay_2_ip = "10.10.0.6"
        relay_3_ip = "10.10.0.7"
        relay_4_ip = "10.10.0.8"
        lamp_0_ip = "10.10.0.15"
        lamp_1_ip = "10.10.0.16"

    if mode == "test":
        lamp_2_ip = "10.10.0.14"
        relay_5_ip = "10.10.0.18"
        relay_1_ip = "10.10.0.5"
        relay_2_ip = "10.10.0.6"
        relay_3_ip = "10.10.0.7"
        relay_4_ip = "10.10.0.8"
        lamp_0_ip = "10.10.0.15"
        lamp_1_ip = "10.10.0.16"

    elif mode == "local":
        # will use mdns names in hope that it make requests more fast
        lamp_2_ip = "10.10.0.14"  # still remote
        relay_5_ip = "10.10.0.18"  # still remote
        relay_1_ip = "esp32_relay_1.local"
        relay_2_ip = "esp32_relay_2.local"
        relay_3_ip = "esp32_relay_3.local"
        relay_4_ip = "esp32_relay_4.local"
        lamp_0_ip = "esp32_pwm_lamp_0.local"
        lamp_1_ip = "esp32_pwm_lamp_1.local"
    else:
        lamp_2_ip = "10.10.0.14"
        relay_5_ip = "10.10.0.18"
        relay_1_ip = "10.10.0.5"
        relay_2_ip = "10.10.0.6"
        relay_3_ip = "10.10.0.7"
        relay_4_ip = "10.10.0.8"
        lamp_0_ip = "10.10.0.15"
        lamp_1_ip = "10.10.0.16"

    sba5_device = HardwareSBA5(
        device_id=99,
        name="SBA5_CO2_sensor"
    )
    # for now just stubs
    lamp0 = HardwareLamp(
        device_id=100,
        name="Lamp_0",
        ip_addr=lamp_2_ip
    )
    relay0 = HardwareRelay(
        device_id=101,
        name="Relay_0",
        channel=0,
        ip_addr= relay_5_ip
    )
    relay1 = HardwareRelay(
        device_id=102,
        name="Relay_1",
        channel=1,
        ip_addr=relay_5_ip
    )
    relay2 = HardwareRelay(
        device_id=103,
        name="Relay_2",
        channel=2,
        ip_addr=relay_5_ip
    )
    relay3 = HardwareRelay(
        device_id=104,
        name="Relay_3",
        channel=3,
        ip_addr=relay_5_ip
    )
    # exp sensors
    exp_ext_temp = HardwareSensorOnRelayBoard(
        device_id=105,
        name="exp_ext_temp",
        description="DHT11 temp outside experimental plants volume",
        family="ext_temp",
        ip_addr=relay_1_ip
    )
    exp_ext_hum = HardwareSensorOnRelayBoard(
        device_id=106,
        name="exp_ext_hum",
        description="DHT11 humidity outside experimental plants volume",
        family="ext_hum",
        ip_addr=relay_1_ip
    )
    exp_int_temp = HardwareSensorOnRelayBoard(
        device_id=107,
        name="exp_int_temp",
        description="DHT22 temp inside experimental plants volume",
        family="int_temp",
        ip_addr=relay_1_ip
    )
    exp_int_hum = HardwareSensorOnRelayBoard(
        device_id=108,
        name="exp_int_hum",
        description="DHT22 hum inside experimental plants volume",
        family="int_hum",
        ip_addr=relay_1_ip
    )
    exp_roots_temp = HardwareSensorOnRelayBoard(
        device_id=109,
        name="exp_roots_temp",
        description="DS18B20 temp inside experimental roots module",
        family="roots_temp",
        ip_addr=relay_1_ip
    )
    # exp relays
    exp_left_vent = HardwareRelay(
        device_id=110,
        name="Exp_vent_left",
        channel=0,
        ip_addr=relay_1_ip
    )
    exp_right_vent = HardwareRelay(
        device_id=111,
        name="Exp_vent_right",
        channel=1,
        ip_addr=relay_1_ip
    )
    exp_left_valve = HardwareRelay(
        device_id=112,
        name="Exp_valve_left",
        channel=2,
        ip_addr=relay_1_ip
    )
    exp_right_valve = HardwareRelay(
        device_id=113,
        name="Exp_valve_right",
        channel=3,
        ip_addr=relay_1_ip
    )
    co2_air_pump = HardwareRelay(
        device_id=114,
        name="CO2_air_pump",
        channel=2,
        ip_addr=relay_2_ip
    )
    co2_valve = HardwareRelay(
        device_id=115,
        name="CO2_valve",
        channel=3,
        ip_addr=relay_2_ip
    )
    exp_lamp = HardwareLamp(
        device_id=116,
        name="Exp_lamp",
        ip_addr=lamp_0_ip
    )
    # control relays and lamp
    control_lamp = HardwareLamp(
        device_id=117,
        name="Control_lamp",
        ip_addr=lamp_1_ip
    )
    control_left_vent = HardwareRelay(
        device_id=118,
        name="Control_vent_left",
        channel=0,
        ip_addr=relay_3_ip
    )
    control_right_vent = HardwareRelay(
        device_id=119,
        name="Control_vent_right",
        channel=1,
        ip_addr=relay_3_ip
    )
    control_left_valve = HardwareRelay(
        device_id=120,
        name="Control_valve_left",
        channel=2,
        ip_addr=relay_3_ip
    )
    control_right_valve = HardwareRelay(
        device_id=121,
        name="Control_valve_right",
        channel=3,
        ip_addr=relay_3_ip
    )
    # control sensors
    control_int_temp = HardwareSensorOnRelayBoard(
        device_id=122,
        name="control_int_temp",
        description="DHT22 temp inside control plants volume",
        family="int_temp",
        ip_addr=relay_3_ip
    )
    control_int_hum = HardwareSensorOnRelayBoard(
        device_id=123,
        name="control_int_hum",
        description="DHT22 hum inside control plants volume",
        family="int_hum",
        ip_addr=relay_3_ip
    )
    control_roots_temp = HardwareSensorOnRelayBoard(
        device_id=124,
        name="control_roots_temp",
        description="DS18B20 temp inside control roots module",
        family="roots_temp",
        ip_addr=relay_3_ip
    )

    # unique_ips = [
    #     lamp_2_ip,
    #     relay_5_ip,
    #     relay_1_ip,
    #     relay_2_ip,
    #     relay_3_ip,
    #     lamp_0_ip,
    #     lamp_1_ip
    #     ]

    global_hardware_collection = HardwareCollection(
        hardware_dict={
            99: sba5_device,
            100: lamp0,
            101: relay0,
            102: relay1,
            103: relay2,
            104: relay3,
            105: exp_ext_temp,
            106: exp_ext_hum,
            107: exp_int_temp,
            108: exp_int_hum,
            109: exp_roots_temp,
            110: exp_left_vent,
            111: exp_right_vent,
            112: exp_left_valve,
            113: exp_right_valve,
            114: co2_air_pump,
            115: co2_valve,
            116: exp_lamp,
            117: control_lamp,
            118: control_left_vent,
            119: control_right_vent,
            120: control_left_valve,
            121: control_right_valve,
            122: control_int_temp,
            123: control_int_hum,
            124: control_roots_temp
        }
    )

    # g.global_hardware_collection.add(lamp0)
    # g.global_hardware_collection.add(relay0)
    # g.global_hardware_collection.add(relay1)
    # g.global_hardware_collection.add(relay2)
    # g.global_hardware_collection.add(relay3)

    # first time store that user-defined hardware collection to redis
    global_hardware_collection.store_hardware_description_to_redis()
    # print("hardware init finished")
    return global_hardware_collection



# def handle_command(device_id: int, command: str, arg: Any):
#     """ method to handle user command from web page for selected device"""
#     # global global_hardware_collection
#     if current_app.global_hardware_collection.length() == 0:
#         raise AssertionError("Hardware has not initialized yet!")
#
#     else:
#         device = current_app.global_hardware_collection.get(int(device_id))
#         device.run_command(command, arg=arg)
#         current_app.global_hardware_collection.store_one_device_update_to_redis(device_id)
#         # TODO: remove sqlite writing here, we will write to sqlite only when state update polling
#         current_app.global_hardware_collection.save_measurement_to_sqlite(device_id)
#         return True

# def get_device_states():
#     # global global_hardware_collection
#     if current_app.global_hardware_collection.length() == 0:
#         raise AssertionError("Hardware has not initialized yet!")
#     else:
#         # print(current_app.global_hardware_collection.load_hardware_description_from_redis())
#         return current_app.global_hardware_collection.load_hardware_description_from_redis()



if __name__ == "__main__":
    # mock call like from real server creation process
    # init_hardware()
    # handle_command(1, "")
    pass
