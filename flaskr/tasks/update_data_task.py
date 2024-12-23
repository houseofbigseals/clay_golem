import sys
sys.path.insert(0, "/opt/clay/clay_golem")
from logging import exception
from flaskr.hardware.hardware_collection import HardwareCollection
from flaskr.db import get_db
from flask import current_app
import os
import time
from flaskr.utils.logger import Logger



def state_update_worker():
    """
    That worker must be run only once. For that purpose we have lock in redis.
    """
    pid = os.getpid()
    redis_client = get_db()
    # Redis keys for commands and task state
    prefix = f"worker:state_update"
    COMMAND_KEY = f"{prefix}:command"
    COMMAND_ARGS_KEY = f"{prefix}:command_args"
    TASK_LOCK_KEY = f"{prefix}:lock"
    TASK_PID_KEY = f"{prefix}:pid"
    TASK_STATUS = f"{prefix}:status"
    logger = Logger.get_logger(f"state_update_worker_{pid}")
    hardware_collection = HardwareCollection.from_redis(redis_client)
    try:
        # Attempt to acquire lock
        if redis_client.set(TASK_LOCK_KEY, "locked", nx=True, ex=10):
            redis_client.set(TASK_PID_KEY, pid)
            logger.info(f"Worker started with PID {pid}")
        else:
            logger.info("Task is already running. Exiting worker.")
            return

        while True:
            logger.info("Trying to load state updates from real devices.")
            hardware_collection.update_all_hardware_info()
            time.sleep(1)

    except Exception as e:
        logger.error(f"Worker with PID {pid} exited with error {e}", exc_info=True)

    finally:
        # Release lock and clean up
        if redis_client.get(TASK_PID_KEY) == str(pid):
            redis_client.delete(TASK_LOCK_KEY)
            redis_client.delete(TASK_PID_KEY)
        logger.info(f"Worker with PID {pid} exited")

def one_ip_update_worker(ip_addr):
    """
    That worker must be run only once. For that purpose we have lock in redis.
    That worker calls only one time for one ip
    """
    pid = os.getpid()
    redis_client = get_db()
    # Redis keys for commands and task state
    prefix = f"worker:update_{ip_addr}"
    COMMAND_KEY = f"{prefix}:command"
    COMMAND_ARGS_KEY = f"{prefix}:command_args"
    TASK_LOCK_KEY = f"{prefix}:lock"
    TASK_PID_KEY = f"{prefix}:pid"
    TASK_STATUS = f"{prefix}:status"
    logger = Logger.get_logger(f"{prefix}_{pid}")
    hardware_collection = HardwareCollection.from_redis(redis_client)
    # Attempt to acquire lock
    if redis_client.set(TASK_LOCK_KEY, "locked", nx=True, ex=10):
        redis_client.set(TASK_PID_KEY, pid)
        logger.info(f"Worker started with PID {pid}")
    else:
        logger.info("Task is already running. Exiting worker.")
        return

    while True:
        try:
            logger.info("Trying to load state updates from real devices.")
            hardware_collection.optimal_device_update(ip_addr)
            redis_client.set(TASK_LOCK_KEY, "locked", nx=True, ex=3)
            time.sleep(1)

        except Exception as e:
            logger.error(f"Worker got error {e}", exc_info=True)



def one_device_update_worker(device_id):
    """
    That worker must be run only once. For that purpose we have lock in redis.
    That worker continuously updates state of only one device
    """
    pid = os.getpid()
    redis_client = get_db()
    # Redis keys for commands and task state
    prefix = f"worker:update_{device_id}:"
    COMMAND_KEY = f"{prefix}:command"
    COMMAND_ARGS_KEY = f"{prefix}:command_args"
    TASK_LOCK_KEY = f"{prefix}:lock"
    TASK_PID_KEY = f"{prefix}:id"
    TASK_STATUS = f"{prefix}:status"
    logger = Logger.get_logger(f"{prefix}_{pid}")
    hardware_collection = HardwareCollection.from_redis(redis_client)

    # Attempt to acquire lock
    if redis_client.set(TASK_LOCK_KEY, "locked", nx=True, ex=10):
        redis_client.set(TASK_PID_KEY, pid)
        logger.info(f"Worker started with PID {pid}")
    else:
        logger.info("Task is already running. Exiting worker.")
        return

    while True:
        try:
            logger.info("Trying to load state updates from real devices.")
            hardware_collection.hardware[device_id].get_info()
            hardware_collection.store_one_device_update_to_redis(device_id)
            hardware_collection.save_measurement_to_sqlite(device_id)
            redis_client.set(TASK_LOCK_KEY, "locked", nx=True, ex=3)
            time.sleep(1)

        except Exception as e:
            logger.error(f"Worker with PID {pid} exited with error {e}", exc_info=True)


