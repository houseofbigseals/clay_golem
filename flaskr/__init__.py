import os
import time
import threading

from flask import Flask, render_template, jsonify, request, current_app
from . import db
from .db import get_db
from .tasks.update_data_task import state_update_worker, one_ip_update_worker, one_device_update_worker
from .tasks.ventilation_task import TaskThread, VentilationTaskThread, ExpVentilationTaskThread, ControlVentilationTaskThread
from .hardware.hardware_config import init_hardware
from .utils.logger import Logger



def create_app():
    # create and configure the app
    instance_path = os.path.join(os.getcwd(), "instance")   # finally
    print(instance_path)
    app = Flask(__name__,  instance_path=instance_path, instance_relative_config=True)

    # print(app.instance_path)
    res = app.config.from_pyfile('config.py')
    print(f"Keys loaded from current app config: {res}")

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    # main page with all controls
    @app.route('/')
    def index():
        with app.app_context():
            devices = current_app.global_hardware_collection.get_device_states()
            return render_template('index.html', devices=devices)

    # обработчик для эксперимента
    @app.route('/handle-experiment', methods=['POST'])
    def handle_experiment():
        try:
            # Получаем данные из JSON-запроса
            data = request.get_json()
            task_id = str(data.get('task_name')) # must be string like worker:ventilation, or worker:search, etc
            command = str(data.get('command'))
            arg = data.get('arg')  # can be int or string
            if arg:
                arg = int(arg)
            # Здесь должна быть логика обработки эксперимента
            # Например, можно вызвать соответствующую функцию из модуля hardware
            
            # Handle the command
            with app.app_context():
                success = current_app.global_hardware_collection.handle_task_command(task_id, command, arg)

                # Получаем данные о задаче вентиляции
                task_data = TaskThread.read_task_data(get_db(), task_id)


            # Return a success response
            if success:
                return jsonify({'status': 'ok', 'task_data': task_data}), 200
            else:
                return jsonify({'status': 'error', 'error': 'Failed to handle task command'}), 500
        except Exception as e:
            app.logger.error(f"Ошибка в обработчике /handle-experiment: {str(e)}", exc_info=True)
            # Return an error response if something goes wrong
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    # handler user commands for all devices
    @app.route('/handle-request', methods=['POST'])
    def handle_request():
        # TODO: do we need to send error responses from low-level devices to wep app ?
        try:
            # Parse the JSON data
            data = request.get_json()

            # Extract the device ID, command, and argument from the data
            # and convert it to correct formats
            device_id = int(data.get('device_id'))
            command = str(data.get('command'))
            arg = data.get('arg')
            if arg:
                arg = int(arg)

            # Handle the command
            with app.app_context():
                success = current_app.global_hardware_collection.handle_command(device_id, command, arg)

            # Return a success response
            if success:
                return jsonify({'status': 'ok'}), 200
            else:
                return jsonify({'status': 'error', 'error': 'Failed to handle command'}), 500
        except Exception as e:
            app.logger.error(f"Ошибка в обработчике /handle-request: {str(e)}", exc_info=True)
            # Return an error response if something goes wrong
            return jsonify({'status': 'error', 'error': str(e)}), 500


    @app.route('/get-device-updates')
    def get_device_updates():
        # `device_states` is a big list with dictionaries holding the state of each device
        with app.app_context():
            new_states = current_app.global_hardware_collection.get_device_states()
            return jsonify(new_states)

    # at first - init database
    db.init_app(app)

    # then - init hardware high level handlers
    # on that step we got ref to HardwareCollection object in current_app


    global_boot_mode = "test"
    unique_ips = {}
    not_online_devices = []
    global_hardware_collection = init_hardware(mode=global_boot_mode)
    unique_ips = global_hardware_collection.unique_ips
    not_online_devices = global_hardware_collection.not_online_devices

    # init tasks
    # start data updating threads
    for ip_addr in unique_ips:
        update_thread = threading.Thread(target=one_ip_update_worker, args=(ip_addr,), daemon=True)
        update_thread.start()

    for dev_id in not_online_devices:
        update_thread = threading.Thread(target=one_device_update_worker, args=(dev_id,), daemon=True)
        update_thread.start()

    # start ventilation task threads
    test_task = VentilationTaskThread(name="worker:test")
    if global_boot_mode == "production":
        exp_vent_task = ExpVentilationTaskThread(name="worker:exp_ventilation")
        control_vent_task = ControlVentilationTaskThread(name="worker:control_ventilation")

    # add task names to hardware collection
    # and start them all
    # current_app.global_hardware_collection.tasks.append(current_app.vent_task.params["name"])
    global_hardware_collection.tasks.append("worker:test")
    if global_boot_mode == "production":
        global_hardware_collection.tasks.append("worker:exp_ventilation")
        global_hardware_collection.tasks.append("worker:control_ventilation")

    with app.app_context():
        current_app.global_hardware_collection = global_hardware_collection
        print(current_app.global_hardware_collection.tasks)

    test_task.start()
    if global_boot_mode == "production":
        exp_vent_task.start()
        control_vent_task.start()



    # init systemd handle cli commands
    #init_systemd_handlers(app)

    return app
