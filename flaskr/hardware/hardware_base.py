import json
import redis
from abc import ABC, abstractmethod
from typing import List, Dict, Type, TypeVar, Union, Any, Tuple
from datetime import datetime

from click import Tuple

from flaskr.drivers import pwm_lamp_driver, esp32_relay_driver, sba5_driver
#from flaskr.utils.leds_calibration import measure   #check if there is an error!
from flaskr.utils.logger import Logger
T = TypeVar('T', bound='Hardware')

# Base class for hardware objects
class Hardware(ABC):
    def __init__(
            self,
            device_id: int,
            name: str,
            params: Dict = None
            ):

        self.params = params  if params else dict()  # i dont want to check it for now
        self.params["device_id"] = device_id
        self.params["name"] = name
        # logger
        self.logger = Logger.get_logger(f"{self.__class__.__name__}_{self.params['name']}")
        # Default hardware cannot keep any commands or data, so initialize as empty dicts
        self.commands = dict()
        self.data = dict()

    def to_dict(self) -> Dict:
        """Convert object to a dictionary representation."""
        return {
            "params": self.params,
            "commands": self.commands,
            "data": self.data,
        }

    @abstractmethod
    def run_command(self, command: str, arg: Any):    # ONLY ONE ARG for simplicity?
        """
        I do not want to make some remote call, it is very unsafe
        So lets every child class implements it itself manually
        """
        pass

    @abstractmethod
    def get_info(self) -> bool:
        """
        get info about state of that particular device
        """
        pass


    @abstractmethod
    def get_raw_info(self) -> [Dict, bool]:  #[Dict, bool]:
        """
        get info about state of all devices, connected to that ip, but not parsed
        """
        pass

    @abstractmethod
    def parse_and_update_info(self, info_dict: Dict):
        """
        parse info message, that was obtained somewhere else
        """
        pass

    def __repr__(self):
        return f"({json.dumps(self.to_dict(), indent=2)})"



# Derived classes for specific hardware


class HardwareRelay(Hardware):
    """
    Relay high-level wrapper
    """
    def __init__(
        self,
        device_id: int, # unique id of device, to use in database and data handling
        name: str,      # human-readable name like "Relay 1"
        ip_addr: str,   # ip addr of real remote relay
        channel: int,   # channel on that relay, must be in [0-3] range
        last_time_active: str = None,
        type: str = "relay",
        uptime_sec: int = 0,
        description: str = "",
        status: str = "unknown",
        last_error: str = "",
    ):

        # Initialize the base class
        super().__init__(
            device_id=device_id,
            name=name
        )
        # it is params, and user cannot change them directly
        self.params["last_time_active"] = last_time_active
        self.params["type"]= type
        self.params["uptime_sec"] = uptime_sec
        self.params["description"] = description
        self.params["status"] = status
        self.params["last_error"] = last_error
        self.params["ip_addr"] = ip_addr
        self.params["channel"] = channel
        # let`s set commands to represent them on web-page
        self.commands["set_on"] = None
        self.commands["set_off"] = None
        self.commands["reset"] = None
        # let`s set data param represent it on web-page
        self.data["state"] = 0
        self.driver = esp32_relay_driver.ESP32RelayDriver(
            host=self.params["ip_addr"],
            name=self.params["name"]
        )
        self.max_commands_repeat = 3
        self.command_repeat_counter = 0

    @classmethod
    def from_redis(cls, redis_client: redis.Redis, device_id: int):
        """
        Class method to create a HardwareRelay object from Redis data.
        Assumes that the Redis client has all necessary keys stored for the device.
        """
        # Fetch the params data as a JSON string from Redis
        data = redis_client.get(f"device:{device_id}:params")

        if data is None:
            raise ValueError(f"Device {device_id} not found in Redis.")

        # Parse the JSON string into a dictionary
        params = json.loads(data)

        # Fetch the commands and data similarly (assuming these are also stored as JSON strings)
        data_data = redis_client.get(f"device:{device_id}:data")

        if data_data:
            data = json.loads(data_data)
        else:
            data = {}

        # Initialize the device from the parsed values
        device = cls(
            device_id=device_id,
            name=params.get("name", ""),
            ip_addr=params.get("ip_addr"),
            channel=int(params.get("channel")),
            last_time_active=params.get("last_time_active"),
            type=params.get("type", "relay"),
            uptime_sec=int(params.get("uptime_sec", 0)),
            description=params.get("description", ""),
            status=params.get("status", "unknown"),
            last_error=params.get("last_error", ""),
        )
        # Restore the data and commands values
        device.data = data
        return device

    def run_command(self, command, **args):
        """
        Manually check available commands for remote procedure calling from web page
        """
        if command == "set_on":
            self.turn_on()
        if command == "set_off":
            self.turn_off()
        if command == "reset":
            self.reset()

    def parse_and_update_info(self, info_dict: Dict):
        ch_id = "ch" + str(self.params["channel"])  # to get str like ch0 or ch2
        self.data["state"] = info_dict[ch_id]
        self.params["uptime"] = info_dict["uptime"]
        self.params["last_time_active"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        self.params["status"] = "ok"

    def get_info(self):
        """

        """
        info_dict = self.driver.get_info()
        if info_dict:
            self.parse_and_update_info(info_dict)
            return True
        else:
            self.params["status"] = "error"
            return False

    def get_raw_info(self):
        info_dict = self.driver.get_info()
        if info_dict:
            return info_dict, True
        else:
            self.params["status"] = "error"
            return {}, False

    def _set_relay_state(self, state: int):
        """
        private method to set relay state
        """
        try:
            success = False
            repeat_counter = 0
            # Устанавливаем состояние реле через драйвер
            while not success:
                success, message = self.driver.set_relay_state(self.params["channel"], state)
                if success:
                    self.data["state"] = state  # Обновляем состояние в данных
                    self.params["status"] = "ok"  # Устанавливаем статус как "ok"
                    self.logger.info(f"{self.params['name']} (ID: {self.params['device_id']}) is now {'ON' if state else 'OFF'}.")
                else:
                    if repeat_counter >= self.max_commands_repeat:
                        self.logger.warning(f"Failed to set relay state: {message}")
                        self.params["status"] = "Error"  # Устанавливаем статус как "Error"
                        self.params["last_error"] = message  # Сохраняем сообщение об ошибке
                    else:
                        repeat_counter +=1

        except Exception as e:
            #TODO а так вообще бывает?
            self.logger.error(e, exc_info=True)
            self.params["last_error"] = str(e)
            self.params["status"] = "Error"  # Устанавливаем статус как "Error"


    def turn_on(self):
        """Turning relay on."""
        self.logger.info("turning relay ON")
        self._set_relay_state(1)


    def turn_off(self):
        """Turning relay off."""
        self.logger.info("turning relay OFF")
        self._set_relay_state(0)

    def reset(self):
        """Сбросить устройство"""
        self.logger.info("Resetting relay...")
        success = self.driver.reset_device()  # Вызов метода reset_device у драйвера

        if success:
            self.params["status"] = "ok"  # Устанавливаем статус как "ok"
            self.logger.info(f"{self.params['name']} (ID: {self.params['device_id']}) has been reset successfully.")
        else:
            self.params["status"] = "Error"  # Устанавливаем статус как "Error"
            self.logger.warning(f"Failed to reset {self.params['name']} (ID: {self.params['device_id']}).")

class HardwareLamp(Hardware):
    """
    PWM lamp high-level wrapper
    """
    def __init__(
            self,
            device_id: int,  # unique id of device, to use in database and data handling
            name: str,  # human-readable name like "Lamp 1"
            ip_addr: str,  # ip addr of real remote Lamp
            last_time_active: str = None,
            type: str = "lamp",
            uptime_sec: int = 0,
            description: str = "",
            status: str = "unknown",
            last_error: str = ""
    ):
        # Initialize the base class
        super().__init__(
            device_id=device_id,
            name=name,
        )
        # params will not change
        self.params["last_time_active"] = last_time_active
        self.params["type"] = type
        self.params["uptime_sec"] = uptime_sec
        self.params["description"] = description
        self.params["status"] = status
        self.params["last_error"] = last_error
        self.params["ip_addr"] = ip_addr
        # let`s set data to represent it on web-page
        # data will change everytime
        self.data["red_pwm_1"] = 0
        self.data["red_pwm_2"] = 0
        self.data["white_pwm_1"] = 0
        self.data["white_pwm_2"] = 0
        self.data["driver_temp"] = 0
        # let`s set commands to represent them on web-page
        self.commands["set_red"] = "int"
        self.commands["set_white"] = "int"
        self.commands["reset"] = None
        # let`s create driver that makes http requests to real device
        self.driver = pwm_lamp_driver.PWMLampDriver(
            host = self.params["ip_addr"],
            name = self.params["name"]
        )
        self.max_command_repeat = 3

    @classmethod
    def from_redis(cls, redis_client: redis.Redis, device_id: int):
        """
        Class method to create a HardwareLamp object from Redis data.
        Assumes that the Redis client has all necessary keys stored for the device.
        """
        # Fetch the params data as a JSON string from Redis
        data = redis_client.get(f"device:{device_id}:params")

        if data is None:
            raise ValueError(f"Device {device_id} not found in Redis.")

        # Parse the JSON string into a dictionary
        params = json.loads(data)
        data_data = redis_client.get(f"device:{device_id}:data")

        if data_data:
            data = json.loads(data_data)
        else:
            data = {}
        # Initialize the device from the parsed values
        device = cls(
            device_id=device_id,
            name=params.get("name", ""),
            ip_addr=params.get("ip_addr", ""),
            last_time_active=params.get("last_time_active"),
            type=params.get("type", "lamp"),
            uptime_sec=int(params.get("uptime_sec", 0)),
            description=params.get("description", ""),
            status=params.get("status", "unknown"),
            last_error=params.get("last_error", ""),
        )

        # Restore the data and commands values
        device.data = data
        return device

    def run_command(self, command, arg):
        """
        Manually check available commands for remote procedure calling from web page
        """
        if command == "set_red":
            self.set_red(arg)
        if command == "set_white":
            self.set_white(arg)
        if command == "reset":
            self.reset()

    def set_pwm(self, color: str, pwm: int):
        """
        Установить значение скважности для указанного цвета.
        Args:
            color (str): Цвет ('red' или 'white')
            pwm (int): Значение скважности
        """
        if color not in ['red', 'white']:
            raise ValueError("Color must be 'red' or 'white'.")

        # Устанавливаем значение скважности
        self.data[f"{color}_pwm_1"] = pwm
        self.data[f"{color}_pwm_2"] = pwm
        self.params["status"] = "ok"  # Статус должен быть "ok"
        self.logger.info(f"Set {color}: {pwm}")

        # Устанавливаем PWM через драйвер
        channel_mapping = {'red': [2, 3], 'white': [0, 1]}
        for channel in channel_mapping[color]:
            # for each channel
            success = False
            repeat_counter = 0
            while not success:
                success, message = self.driver.set_pwm(channel, pwm)
                if success:
                    self.logger.debug(f"Successfully set PWM on channel {channel}: {message}")
                else:
                    if repeat_counter >= self.max_command_repeat:
                        self.params["status"] = "Error"  # Устанавливаем статус как "Error"
                        self.params["last_error"] = message  # Сохраняем сообщение об ошибке
                        self.logger.error(f"Failed to set {color} PWM on channel {channel}: {message}")
                    else:
                        repeat_counter +=1

    def set_red(self, pwm: int):
        self.set_pwm('red', pwm)

    def set_white(self, pwm: int):
        self.set_pwm('white', pwm)

    def reset(self):
        self.logger.info(f"Reset lamp")
        
        try:
            success, message = self.driver.reset_device() 
            if success:
                self.params["status"] = "ok"  # Устанавливаем статус как "ok"
                self.logger.info(f"{self.params['name']} (ID: {self.params['device_id']}) has been reset successfully.")
            else:
                self.params["status"] = "Error"  # Устанавливаем статус как "Error"
                self.logger.warning(f"Failed to reset {self.params['name']} (ID: {self.params['device_id']}). Message: {message}")
                self.params["last_error"] = message
        except Exception as e:
                self.logger.error(e)
                self.params["last_error"] = str(e)
                self.params["status"] = "Error"  # Устанавливаем статус как "Error"


    def parse_and_update_info(self, info_dict: Dict):
        self.data["white_pwm_1"] = info_dict["ch0_pwm"]
        self.data["white_pwm_2"] = info_dict["ch1_pwm"]
        self.data["red_pwm_1"] = info_dict["ch2_pwm"]
        self.data["red_pwm_2"] = info_dict["ch3_pwm"]
        self.data["driver_temp"] = round(info_dict["pcb_temp"], 2)
        self.params["uptime"] = info_dict["uptime"]
        self.params["last_time_active"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        self.params["status"] = "ok"

    def get_info(self):
        """

        """
        info_dict = self.driver.get_info()
        if info_dict:
            self.parse_and_update_info(info_dict)
            return True
        else:
            self.params["status"] = "error"
            return False

    def get_raw_info(self):
        info_dict = self.driver.get_info()
        if info_dict:
            return info_dict, True
        else:
            self.params["status"] = "error"
            return {}, False



# class HardwareHumSensor(Hardware):
#     """
#
#     """
#
#     pass

class HardwareSensorOnRelayBoard(Hardware):
    """
    Handler for sensors, those mounted on relay board
    https://github.com/houseofbigseals/esp32_relay
    """
    def __init__(
            self,
            device_id: int,  # unique id of device, to use in database and data handling
            name: str,  # human-readable name like "Hum sensor 12"
            ip_addr: str,  # ip addr of real remote sensor
            family: str,  # TODO: family can be  .... ? "roots_temp", "ext_temp", "ext_hum", "int_temp", "int_hum"
            last_time_active: str = None,
            type: str = "sensor",
            uptime_sec: int = 0,
            description: str = "",
            status: str = "unknown",
            last_error: str = ""
    ):
        # Initialize the base class
        super().__init__(
            device_id=device_id,
            name=name,
        )

        # it is params, and user cannot change them directly
        self.params["last_time_active"] = last_time_active
        self.params["type"]= type
        self.params["family"] = family
        self.params["uptime_sec"] = uptime_sec
        self.params["description"] = description
        self.params["status"] = status
        self.params["last_error"] = last_error
        self.params["ip_addr"] = ip_addr
        # let`s set commands to represent them on web-page
        self.commands["---"] = None
        # let`s set data param represent it on web-page
        if (family == "roots_temp") or (family == "ext_temp") or (family == "int_temp"):
            self.data["temp"] = 0
            self.params["units"] = "°C"
            self.logger.info(f"created device {name} in family {family}")
        elif (family == "ext_hum") or (family == "int_hum"):
            self.data["hum"] = 0
            self.params["units"] = "%"
            self.logger.info(f"created device {name} in family {family}")
        # it is weird, but sensors connected to relay pcb, so ...
        self.driver = esp32_relay_driver.ESP32RelayDriver(
            host=self.params["ip_addr"],
            name=self.params["name"]
        )
        # for d in self.data:
        #     self.logger.info(f"device {name} in family {family} has {d}")

    @classmethod
    def from_redis(cls, redis_client: redis.Redis, device_id: int):
        """
        Class method to create a HardwareSensorOnRelayBoard object from Redis data.
        Assumes that the Redis client has all necessary keys stored for the device.
        """
        # Fetch the params data as a JSON string from Redis
        data = redis_client.get(f"device:{device_id}:params")

        if data is None:
            raise ValueError(f"Device {device_id} not found in Redis.")

        # Parse the JSON string into a dictionary
        params = json.loads(data)

        # Fetch the commands and data similarly (assuming these are also stored as JSON strings)
        commands_data = redis_client.get(f"device:{device_id}:commands")
        data_data = redis_client.get(f"device:{device_id}:data")

        if commands_data:
            commands = json.loads(commands_data)
        else:
            commands = {}

        if data_data:
            data = json.loads(data_data)
        else:
            data = {}

        # Initialize the device from the parsed values
        family = params.get("family", "unknown")
        device = cls(
            device_id=device_id,
            name=params.get("name", ""),
            ip_addr=params.get("ip_addr", ""),
            family=family,
            last_time_active=params.get("last_time_active"),
            type=params.get("type", "sensor"),
            uptime_sec=int(params.get("uptime_sec", 0)),
            description=params.get("description", ""),
            status=params.get("status", "unknown"),
            last_error=params.get("last_error", ""),
        )

        # Restore the data and commands values
        device.commands = commands
        device.data = data
        return device

    def run_command(self, command, arg):
        """
        I do not want to make some remote call, it is very unsafe
        So lets every child class implements it itself manually
        """
        # sensors have no commands
        return True

    def parse_and_update_info(self, info_dict: Dict):
        code_name = self.params["family"]
        self.params["uptime"] = info_dict["uptime"]
        if (code_name == "roots_temp") or (code_name == "ext_temp") or (code_name == "int_temp"):
            temp = info_dict[code_name]
            if temp == self.driver.SENSOR_ERROR_VALUE:
                self.params["status"] = "Error"
                return False
            else:
                self.data["temp"] = round(info_dict[code_name], 2)

        elif code_name == "ext_hum" or code_name == "int_hum":
            hum = info_dict[code_name]
            if hum == self.driver.SENSOR_ERROR_VALUE:
                self.params["status"] = "Error"
                return False
            else:
                self.data["hum"] = round(info_dict[code_name], 2)
        self.params["last_time_active"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        self.params["status"] = "ok"

    def get_info(self):
        """
        get info about state of that particular device
        """
        info_dict = self.driver.get_info()
        # self.logger.debug(self.params["device_id"])
        if info_dict:
            self.parse_and_update_info(info_dict)
            return True
        else:
            return False

    def get_raw_info(self):
        info_dict = self.driver.get_info()
        if info_dict:
            return info_dict, True
        else:
            return {}, False


class HardwareSBA5(Hardware):
    """
        Handler for SBA5 sensor, that connected to serial port
        """

    def __init__(
            self,
            device_id: int,  # unique id of device, to use in database and data handling
            name: str,  # human-readable name like "Hum sensor 12"
            family: str = "SBA5",
            last_time_active: str = None,
            type: str = "sensor",
            description: str = "",
            status: str = "unknown",
            last_error: str = ""
    ):
        # Initialize the base class
        super().__init__(
            device_id=device_id,
            name=name,
        )

        # it is params, and user cannot change them directly
        self.params["last_time_active"] = last_time_active
        self.params["type"] = type
        self.params["family"] = family
        self.params["description"] = description
        self.params["status"] = status
        self.params["units"] = "ppm co2"
        self.params["last_error"] = last_error
        # let`s set commands to represent them on web-page
        self.commands["---"] = None
        # let`s set data param represent it on web-page
        self.data["co2"] = 0
        # This sensor connected only to exp pc, so
        try:
            self.driver = sba5_driver.SBAWrapper()  # default settings
        except Exception as e:
            self.driver = None
            self.params["status"] = "Not connected"
            self.logger.warning(str(e), exc_info=True)  # reduce that error to warning

    @classmethod
    def from_redis(cls, redis_client: redis.Redis, device_id: int):
        """
        Class method to create a HardwareSBA5 object from Redis data.
        Assumes that the Redis client has all necessary keys stored for the device.
        """
        # Fetch the params data as a JSON string from Redis
        data = redis_client.get(f"device:{device_id}:params")

        if data is None:
            raise ValueError(f"Device {device_id} not found in Redis.")

        # Parse the JSON string into a dictionary
        params = json.loads(data)

        # Fetch the commands and data similarly (assuming these are also stored as JSON strings)
        commands_data = redis_client.get(f"device:{device_id}:commands")
        data_data = redis_client.get(f"device:{device_id}:data")

        if data_data:
            data = json.loads(data_data)
        else:
            data = {}

        # Initialize the device from the parsed values
        device = cls(
            device_id=device_id,
            name=params.get("name", ""),
            family=params.get("family", "SBA5"),
            last_time_active=params.get("last_time_active"),
            type=params.get("type", "sensor"),
            description=params.get("description", ""),
            status=params.get("status", "unknown"),
            last_error=params.get("last_error", ""),
        )

        # Restore the data and commands values
        device.data = data
        return device

    def run_command(self, command, arg):
        """
        I do not want to make some remote call, it is very unsafe
        So lets every child class implements it itself manually
        """
        # sensors have no commands
        return True

    def get_info(self):
        """
        get info about state of that particular device
        """
        if self.driver:
            # if device really exist
            m = self.driver.error_code
            while m == self.driver.error_code:
                # we will answer the device until get normal result
                raw_data, m = self.driver.get_measure()
                if "Error:" in raw_data:
                    # that means that something went critically wrong
                    self.params["status"] = "error"
                    # stop that cycle
                    return False

            if m != self.driver.error_code:
                self.data["co2"] = m
                self.params["last_time_active"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
                self.params["status"] = "ok"
            return True
        else:
            return False

    def get_raw_info(self):
        """ it is offline device, so no additional raw info is available"""
        pass

    def parse_and_update_info(self, info_dict: Dict):
        """Do not use that method, just call get_info instead"""
        pass


if __name__ == "__main__":
    pass