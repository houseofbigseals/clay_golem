from sys import exc_info

from flask import app, current_app
import os
from flaskr.db import get_db
import time
from threading import Thread, Event
from datetime import datetime, timedelta
from flaskr.utils.logger import Logger
from flaskr.hardware.hardware_base import HardwareRelay
from flaskr.drivers.esp32_relay_driver import ESP32RelayDriver
from flaskr.drivers.pwm_lamp_driver import PWMLampDriver
import json
import redis


# TODO: make here base class to store in hardware collection

class TaskThread(Thread):
    """

    """
    def __init__(self,  name):
        super().__init__()


        self.redis_client = get_db()
        self.kill_event = Event()
        self.daemon = True  # Ensures the thread stops when the main program exits
        # Redis keys for commands and task state
        pid = os.getpid()
        prefix = name if name else "worker:unknown"
        self.COMMAND_KEY = f"{prefix}:user_command"
        self.COMMAND_ARGS_KEY = f"{prefix}:command_args"
        self.TASK_LOCK_KEY = f"{prefix}:lock"
        self.TASK_PID_KEY = f"{prefix}:pid"
        self.TASK_PARAMS = f"{prefix}:params"
        self.TASK_STAGES = f"{prefix}:stages"
        self.TASK_COMMANDS = f"{prefix}:commands"
        self.logger = Logger.get_logger(f"{prefix}_{pid}")

        # stages and numbers for future
        self.stages = {
            0: "idle"
        }
        self.commands = {
            "start": "Run task from current step",
            "stop": "Stop task on current step",
            "ping": "Dump info about that task to redis now",
            "reset": "Set current task to 0 and stop",
            "kill": "Kill task and exit"
        }
        # define params
        self.params = {
            "last_user_command": None,
            "last_response": datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
            "type": "task",
            "name": prefix,
            "status": "unknown",
            "pid": pid,
            "step": 0,
            "running": False,
            "current_stage_name": self.stages[0]
        }
        self.data = {}
        # Attempt to acquire lock
        if self.redis_client.set(self.TASK_LOCK_KEY, "locked", nx=True, ex=10):
            self.redis_client.set(self.TASK_PID_KEY, pid)

            self.logger.info(f"{prefix} started with PID {pid}")
            self.create_drivers()
            # save it all to redis first time
            self._write_status()
        else:
            self.kill_event.set()
            print("we are not the chosen one")
            self.logger.info("Ventilation task is already running. Exiting worker.")
            return

    def create_drivers(self):
        pass

    def _write_status(self):
        """Write the current step and timestamp to Redis."""
        self.redis_client.set(self.TASK_LOCK_KEY, "locked", nx=True, ex=2)
        self.redis_client.set(self.TASK_PARAMS, json.dumps(self.params))
        self.redis_client.set(self.TASK_COMMANDS, json.dumps(self.commands))
        self.redis_client.set(self.TASK_STAGES, json.dumps(self.stages))

    def main_work(self, step):
        pass

    def run(self):
        """The task's thread main loop."""
        while not self.kill_event.is_set():
            # infinite loop
            try:
                # first - read new user command
                command = self.redis_client.get(self.COMMAND_KEY)
                self.params["status"] = "ok"
                if command:
                    self.params["last_user_command"] = command
                if command == "start" and not self.params["running"] :
                    self.redis_client.delete(self.COMMAND_KEY)  # Clear the command
                    self.params["running"] = True
                    self.logger.info(f"start work from step {self.params['step']}")
                elif command == "stop" and self.params["running"] :
                    self.redis_client.delete(self.COMMAND_KEY)  # Clear the command
                    self.params["running"] = False
                    self.logger.info(f"Stop command received: stop vent task at step {self.params['step']}")
                elif command == "reset":
                    self.redis_client.delete(self.COMMAND_KEY)
                    self.params["step"] = 0
                    self.params["current_stage_name"] = self.stages[0]
                    self.params["running"] = False
                    self.logger.info("Reset command received: set current step to 0 and stop")
                elif command == "ping":
                    self.redis_client.delete(self.COMMAND_KEY)
                    self._write_status()
                    self.logger.info("pong")
                elif command == "kill":
                    self.params["status"] = "killed"
                    self.logger.info("Kill command received")
                    self.redis_client.delete(self.COMMAND_KEY)
                    self.kill_event.set()

                # after command checking - work
                self.main_work(self.params["step"])
            except Exception as e:
                self.logger.error(f"Error in task loop: {e}", exc_info=True)
                self.params["status"] = "error"
                self.params["last_error"] = str(e)
            self._write_status()
            time.sleep(1)  # Periodic check for new commands

    def kill(self):
        """Kill the thread gracefully from outside."""
        self.kill_event.set()

    def stop(self):
        """Stop the thread from outside."""
        self.params["running"] = False

    @classmethod
    def read_task_data(cls, redis_client, task_prefix="worker:ventilation"):
        """
        Reads and returns all data about the task from Redis.

        :param redis_client: Redis connection instance
        :param task_prefix: Prefix for Redis keys related to the task
        :return: Dictionary containing task params, commands, and stages
        """
        try:
            params = redis_client.get(f"{task_prefix}:params")
            commands = redis_client.get(f"{task_prefix}:commands")
            stages = redis_client.get(f"{task_prefix}:stages")

            # Parse JSON strings to dictionaries
            task_data = {
                "params": json.loads(params) if params else {},
                "commands": json.loads(commands) if commands else {},
                "stages": json.loads(stages) if stages else {},
                "data": {}    # aaaaaaaaaaaaaaaaaaaaa
            }
            return task_data
        except Exception as e:
            Logger.get_logger("fuuuu").error(f"error getting task data{e}", exc_info=True)
            return {}

    @classmethod
    def write_task_command(cls, redis_client, task_prefix="worker:ventilation", command=None, args=None):
        """
        Writes a command and optional arguments to Redis for the task.

        :param redis_client: Redis connection instance
        :param task_prefix: Prefix for Redis keys related to the task
        :param command: Command to write (e.g., "start", "stop", "reset", "kill", "ping")
        :param args: Optional arguments for the command
        """
        try:
            if command:
                redis_client.set(f"{task_prefix}:user_command", command)
            if args:
                redis_client.set(f"{task_prefix}:command_args", json.dumps(args))
            Logger.get_logger("fuuuu").info(f"command {command} for task {task_prefix} is written to redis")
        except Exception as e:
            Logger.get_logger("fuuuu").error(f"error writing task command: {e}", exc_info=True)


class VentilationTaskThread(TaskThread):
    """
    Overcomplicated task for test remote devices
    """

    def __init__(self, name="worker:ventilation"):
        super().__init__(name=name)
        self.stages = {
            0: "idle",
            1: "part1",
            2: "part2",
            3: "part3",
            4: "part4"
        }

    def create_drivers(self):
        # create drivers
        # YES, THEY ARE HARDCODED
        self.relay = ESP32RelayDriver("10.10.0.18", name=self.name)

    def main_work(self, step):
        """The main work of the task, divided into steps."""
        # make one step and exit
        if self.params["running"] and not self.kill_event.is_set():
            if step == 0:
                self.logger.info("step 0 - idle")
                self.relay.set_relay_state(channel=0, state=0)
                self.relay.set_relay_state(channel=1, state=0)
                self.relay.set_relay_state(channel=2, state=0)
                self.relay.set_relay_state(channel=3, state=0)
                # Just sleep for 10 seconds
                time.sleep(10)  # Example work duration
                self.params["step"] += 1
            elif step == 1:
                self.logger.info("step 1")
                self.relay.set_relay_state(channel=0, state=1)
                time.sleep(5)
                self.params["step"] += 1
            elif step == 2:
                self.logger.info("step 2")
                self.relay.set_relay_state(channel=1, state=1)
                time.sleep(5)
                self.params["step"] += 1
            elif step == 3:
                self.logger.info("step 3")
                self.relay.set_relay_state(channel=2, state=1)
                time.sleep(5)
                self.params["step"] += 1
            elif step == 4:
                self.logger.info("step 4")
                self.relay.set_relay_state(channel=3, state=1)
                time.sleep(5)
                self.params["step"] = 0

            # finally update params
            self.params["last_response"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            self.params["current_stage_name"] = self.stages[self.params["step"]]
            self._write_status()

class ExpVentilationTaskThread(TaskThread):
    """
    Class for exp plants volume ventilation automation
    """
    def __init__(self, name):
        super().__init__(name=name)
        self.stages = {
            0: "idle",
            1: "opening valves",
            2: "ventilation",
            3: "shutting down valves and vents"
        }
        self.timer = datetime.now()
        self.wait_vent_flag = False
        self.params["period"] = 10   # mins
        self.params["ventilation_time"] = 240  # sec
        self.params["running"] = True   # that task is active by default
        self.next_work_time = self.calculate_next_work_time()
        self.params["next_run"] = self.next_work_time.strftime("%d-%m-%Y %H:%M:%S")
        self.logger.info(f"next run time scheduled to {self.params['next_run']}")


    def calculate_next_work_time(self) -> datetime:
        """ calculate next period of activity"""
        now = datetime.now()
        now = now.replace(second=0, microsecond=0)
        next_run_minute = ((now.minute // self.params["period"]) + 1) * self.params["period"]
        delta_minutes = next_run_minute - now.minute
        next_run_time = now + timedelta(minutes=delta_minutes)
        return next_run_time

    def create_drivers(self):
        # create drivers
        # YES, THEY ARE HARDCODED
        # exp_left_vent = HardwareRelay(
        #     device_id=110,
        #     name="Exp_vent_left",
        #     channel=0,
        #     ip_addr="10.10.0.5"
        # )
        # exp_right_vent = HardwareRelay(
        #     device_id=111,
        #     name="Exp_vent_right",
        #     channel=1,
        #     ip_addr="10.10.0.5"
        # )
        # exp_left_valve = HardwareRelay(
        #     device_id=112,
        #     name="Exp_valve_left",
        #     channel=2,
        #     ip_addr="10.10.0.5"
        # )
        # exp_right_valve = HardwareRelay(
        #     device_id=113,
        #     name="Exp_valve_right",
        #     channel=3,
        #     ip_addr="10.10.0.5"
        # )
        self.relay = ESP32RelayDriver("10.10.0.5", self.name)

    def main_work(self, step):
        """The main work of the task, divided into steps."""
        # make one step and exit

        if self.params["running"] and not self.kill_event.is_set():
            if step == 0:
                # idle part
                # just check if the time is come
                self.logger.debug("step 0 - idle")
                if datetime.now() >= self.next_work_time:
                    # time to run!!!!
                    self.params["step"] = 1  # next step - open valves
                else:
                    # ensure they are closed
                    # self.vent1.turn_off()
                    # self.vent2.turn_off()
                    # self.valve1.turn_off()
                    # self.valve2.turn_off()
                    # Just sleep
                    time.sleep(1)
            elif step == 1:
                # open valves
                self.logger.info("step 1: open valves")
                self.relay.set_relay_state(channel=2, state=1)
                self.relay.set_relay_state(channel=3, state=1)
                time.sleep(5) # it is time to be sure that valves fully opened
                self.params["step"] = 2  # nest step - turn on vents
            elif step == 2:
                # start ventilation
                if not self.wait_vent_flag:
                    self.logger.info("step 2: start ventilation")
                    self.relay.set_relay_state(channel=0, state=1)
                    self.relay.set_relay_state(channel=1, state=1)
                    self.timer = datetime.now() + timedelta(seconds=self.params["ventilation_time"])  #
                    self.wait_vent_flag = True
                else:
                    if datetime.now() > self.timer:
                        self.logger.info("step 2: ventilation time ended")
                        self.params["step"] = 3
                        self.wait_vent_flag = False
                    else:
                        self.logger.info("step 2: ventilation time is not ended")
                        time.sleep(2)
            elif step == 3:
                # stop ventilation
                self.logger.info("step 3: stop ventilation")
                self.relay.set_relay_state(channel=0, state=0)
                self.relay.set_relay_state(channel=1, state=0)
                self.relay.set_relay_state(channel=2, state=0)
                self.relay.set_relay_state(channel=3, state=0)
                self.next_work_time = self.calculate_next_work_time()
                self.params["next_run"] = self.next_work_time.strftime("%d-%m-%Y %H:%M:%S")
                self.logger.info(f"next run time scheduled to {self.params['next_run']}")
                time.sleep(5)
                self.params["step"] = 0


            # finally update params
            self.params["last_response"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            self.params["current_stage_name"] = self.stages[self.params["step"]]
            self._write_status()


class ControlVentilationTaskThread(TaskThread):
    """
    Class for control plants volume ventilation automation
    """
    def __init__(self, name):
        super().__init__(name=name)
        self.stages = {
            0: "idle",
            1: "opening valves",
            2: "ventilation",
            3: "shutting down valves and vents"
        }
        self.timer = datetime.now()
        self.wait_vent_flag = False
        self.params["period"] = 10   # mins
        self.params["ventilation_time"] = 240  # sec
        self.params["running"] = True   # that task is active by default
        self.next_work_time = self.calculate_next_work_time()
        self.params["next_run"] = self.next_work_time.strftime("%d-%m-%Y %H:%M:%S")
        self.logger.info(f'next run time scheduled to {self.params["next_run"]}')


    def calculate_next_work_time(self) -> datetime:
        """ calculate next period of activity"""
        now = datetime.now()
        now = now.replace(second=0, microsecond=0)
        next_run_minute = ((now.minute // self.params["period"]) + 1) * self.params["period"]
        delta_minutes = next_run_minute - now.minute
        next_run_time = now + timedelta(minutes=delta_minutes)
        return next_run_time

    def create_drivers(self):
        # create drivers
        self.relay = ESP32RelayDriver("10.10.0.7", self.name)

    def main_work(self, step):
        """The main work of the task, divided into steps."""
        # make one step and exit
        if self.params["running"] and not self.kill_event.is_set():
            if step == 0:
                # idle part
                # just check if the time is come
                self.logger.debug("step 0 - idle")
                if datetime.now() >= self.next_work_time:
                    # time to run!!!!
                    self.params["step"] = 1  # next step - open valves
                else:
                    # Just sleep
                    time.sleep(1)
            elif step == 1:
                # open valves
                self.logger.info("step 1: open valves")
                self.relay.set_relay_state(channel=2, state=1)
                self.relay.set_relay_state(channel=3, state=1)
                time.sleep(5) # it is time to be sure that valves fully opened
                self.params["step"] = 2  # nest step - turn on vents
            elif step == 2:
                # start ventilation
                if not self.wait_vent_flag:
                    self.logger.info("step 2: start ventilation")
                    self.relay.set_relay_state(channel=0, state=1)
                    self.relay.set_relay_state(channel=1, state=1)
                    self.timer = datetime.now() + timedelta(seconds=self.params["ventilation_time"])  #
                    self.wait_vent_flag = True
                else:
                    if datetime.now() > self.timer:
                        self.logger.info("step 2: ventilation time ended")
                        self.params["step"] = 3
                        self.wait_vent_flag = False
                    else:
                        self.logger.info("step 2: ventilation time is not ended")
                        time.sleep(2)
            elif step == 3:
                # stop ventilation
                self.logger.info("step 3: stop ventilation")
                self.relay.set_relay_state(channel=0, state=0)
                self.relay.set_relay_state(channel=1, state=0)
                self.relay.set_relay_state(channel=2, state=0)
                self.relay.set_relay_state(channel=3, state=0)
                self.next_work_time = self.calculate_next_work_time()
                self.params["next_run"] = self.next_work_time.strftime("%d-%m-%Y %H:%M:%S")
                self.logger.info(f"next run time scheduled to {self.params['next_run']}")
                time.sleep(5)
                self.params["step"] = 0


            # finally update params
            self.params["last_response"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            self.params["current_stage_name"] = self.stages[self.params['step']]
            self._write_status()



if __name__ == "__main__":
    pass
    # now = datetime(2024, 3, 31, 23, 57, 54, 720267)
    # now = datetime.now()
    # now = now.replace(second=0, microsecond=0)
    # next_run_minute = ((now.minute // 15) + 1) * 15
    # delta_minutes = next_run_minute - now.minute
    # next_run_time = now + timedelta(minutes=delta_minutes)
    # print(f"Scheduling next run at {next_run_time}")
    redis_host = 'localhost'
    redis_port = 6379
    task_prefix = "worker:ventilation"
    redis_client = redis.StrictRedis(host=redis_host, port=redis_port, decode_responses=True)
    # TaskThread.write_task_command(redis_client, "worker:ventilation", "start")
    # TaskThread.write_task_command(redis_client, "worker:exp_ventilation", "start")
    task_data = TaskThread.read_task_data(redis_client, "worker:ventilation")
    task_data2 = TaskThread.read_task_data(redis_client, "worker:exp_ventilation")
    print(json.dumps(task_data, indent=4))
    print(json.dumps(task_data2, indent=4))
    # time.sleep(10)
    # task_data = VentilationTaskThread.read_task_data()
    # print(json.dumps(task_data, indent=4))

