// button hide/show data handler
function toggleVisibility(id) {
    var x = document.getElementById(id);
    if (x.style.display === "none") {
        x.style.display = "block";
    } else {
        x.style.display = "none";
    }
}
// change color of status indicator
document.addEventListener('DOMContentLoaded', function() {
    const statusIndicators = document.querySelectorAll('.status-indicator');
    statusIndicators.forEach(indicator => {
        const status = indicator.textContent.trim();
        indicator.className += status === 'ok' ? ' status-ok' : ' status-error';
    });
});
// ajax polling to update data
function updateDeviceValues() {
    $.ajax({
        url: '/get-device-updates', // The Flask route that returns updated device info
        type: 'GET',
        dataType: 'json', // Expect JSON data in response
        success: function(devices) {
            devices.forEach(handleDeviceUpdate);
            devices.filter(device => device.params.type === 'task')
                .forEach(handleExperimentUpdate)
        },
        error: function(xhr, status, error) {
            console.error("Error fetching device updates:", status, error);
        }
    });
}

// Initialize Bootstrap tabs
$('#myTab a').on('click', function (e) {
    e.preventDefault();
    $(this).tab('show');
});

function handleDeviceUpdate(device) {
    // Update parameters and data for each device
    // Assuming the device ID is unique and can be used to target the elements
    $(`#device${device.params.device_id}_status_indicator`).text(device.params.status);
    $(`#device${device.params.device_id}_last_response`).text(device.params.last_time_active);

    // Update status class based on the device status
    const statusClass = device.params.status === 'ok' ? 'status-ok' : 'status-error';
    $(`#device${device.params.device_id}_status_indicator`)
        .removeClass('status-ok status-error')
        .addClass(statusClass);

    // Update Parameters Table
    updateParamsTable(device);

    // Update Data Table
    updateDataTable(device);

}

function handleExperimentUpdate(task){
    // Обновляем прогресс-бар
    updateProgressBar(task);
    updateExperimentParamsTable(task)
    updateExperimentStatus(task)
}

function updateDataTable(device) {
    const dataTable = $(`#dataTable${device.params.device_id} tbody`); // Assuming the data table directly follows the device div
    dataTable.empty(); // Clear existing rows
    $.each(device.data, function (dataKey, dataValue) {
        dataTable.append(`<tr><td>${dataKey}</td><td>${dataValue}</td></tr>`);
    });
}

function updateParamsTable(device) {
    const paramsTable = $(`#paramsTable${device.params.device_id} tbody`);
    paramsTable.empty(); // Clear existing rows
    $.each(device.params, function (param, value) {
        paramsTable.append(`<tr><td>${param}</td><td>${value}</td></tr>`);
    });
}

function updateProgressBar(device) {
    if(device.params.type == "task"){
        task_postfix = device.params.name.replace(':', '-')
        const progressBar = document.getElementById('progress-bar'+task_postfix);
        if (progressBar) {
            const totalStages = Object.keys(device.stages).length;
            const step = device.params.step;; // Извлекаем значение step
            const progressPercentage = (step / totalStages) * 100; // Предположим, что максимальный шаг 4
            progressBar.style.width = progressPercentage + '%';
            progressBar.setAttribute('aria-valuenow', progressPercentage);
            progressBar.innerText = Math.round(progressPercentage) + '%'; // Обновляем текст прогресс-бара
        } else {
            console.error('Element with id "progress-bar${task_postfix}" not found.');
        }
    }
}

function updateExperimentParamsTable(task){
        // Обновляем параметры в модальном окне
        task_postfix = task.params.name.replace(':', '-')
        const paramsTable = $(`#paramsTable${task_postfix} tbody`);
        paramsTable.empty(); // Очищаем существующие строки
        $.each(task.params, function(param, value) {
            paramsTable.append(`<tr><td>${param}</td><td>${value}</td></tr>`);
        });
}

function updateExperimentStatus(task){
    task_postfix = task.params.name.replace(':', '-')
    const experimentStatusElement = document.getElementById('experiment-status'+task_postfix);
    if (experimentStatusElement) {
        experimentStatusElement.innerText = task.params.status;
    } else {
        console.error('Element with id "experiment-status" not found.');
    }
    document.getElementById('last-update'+task_postfix).innerText = task.params.last_response;
}

function sendExperimentCommand(task_name) {
    task_postfix = task_name.replace(':', '-')
    const command = document.getElementById('command-select'+task_postfix).value;
    const args = document.getElementById('command-args'+task_postfix).value;

    $.ajax({
        url: '/handle-experiment',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ command: command, args: args, task_name: task_name }),
        success: function(response) {
            // Обновляем статус и время последнего обновления
            const experimentStatusElement = document.getElementById('experiment-status'+task_postfix);
            if (experimentStatusElement) {
                experimentStatusElement.innerText = response.status;
            } else {
                console.error('Element with id "experiment-status" not found.');
            }
            document.getElementById('last-update'+task_postfix).innerText = new Date().toLocaleString();
            // document.getElementById('ventilation-task-data').innerText = JSON.stringify(response.task_data, null, 2); // Отображаем данные о задаче

            // Обновляем прогресс-бар
            const progressBar = document.getElementById('progress-bar'+task_postfix);
            if (progressBar) {
                const stages = response.task_data.stages
                const step_count = Object.keys(stages).length
                const step = response.task_data.params.step; // Извлекаем значение step
                const progressPercentage = (step / step_count) * 100; // Предположим, что максимальный шаг 4
                progressBar.style.width = progressPercentage + '%';
                progressBar.setAttribute('aria-valuenow', progressPercentage);
                progressBar.innerText = Math.round(progressPercentage) + '%'; // Обновляем текст прогресс-бара
            } else {
                console.error('Element with id "progress-bar" not found.');
            }

            // Обновляем параметры в модальном окне
            const paramsTable = $(`#paramsTable${task_postfix} tbody`);
            paramsTable.empty(); // Очищаем существующие строки
            $.each(response.task_data.params, function(param, value) {
                paramsTable.append(`<tr><td>${param}</td><td>${value}</td></tr>`);
            });

            createAlert(`Команда "${command}" успешно отправлена.`, 'success');
        },
        error: function(xhr, status, error) {
            console.error('Ошибка при отправке команды эксперимента:', error);
            createAlert(`Ошибка! ${xhr.responseJSON.message}`, 'danger');
        }
    });
}
function sendCommand(deviceId) {
    // Get the command and argument values
    const command = $(`#device${deviceId}_command`).val();
    const arg = $(`#device${deviceId}_arg`).val();

    // Send POST request
    $.ajax({
        url: '/handle-request',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ device_id: deviceId, command: command, arg: arg }),
        dataType: 'json',
        success: function(response) {
            // Check the response status
            if(response.status === 'ok') {
                // Create a success alert
                createAlert('Success! Command has been sent successfully.', 'success');
            } else {
                // Create an error alert with the error message
                createAlert(`Error! ${response.error}`, 'danger');
            }
        },
        error: function(xhr, status, error) {
            let errorMessage = 'Error sending command to the device.';
            // Check for different types of errors
            if (xhr.status === 0) {
                errorMessage = 'Cannot connect to the server.';
            } else if (xhr.status === 404) {
                errorMessage = 'The requested resource was not found (404).';
            } else if (xhr.status === 500) {
                errorMessage = 'Internal Server Error (500).';
            } else if (error === 'parsererror') {
                errorMessage = 'Requested JSON parse failed.';
            } else if (error === 'timeout') {
                errorMessage = 'Time out error.';
            } else if (error === 'abort') {
                errorMessage = 'Ajax request aborted.';
            } else {
                errorMessage = `Uncaught Error.\n${xhr.responseText}`;
            }

            // Create an error alert with the detailed error message
            createAlert(errorMessage, 'danger');
        }
    });
}

function createAlert(message, type) {
    // Create a unique ID for the alert
    const uniqueId = `alert-${Date.now()}`;
    const alertHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert" id="${uniqueId}">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    // Prepend the alert to the container or body
    $("body").prepend(alertHTML);

    // Optional: Automatically remove the alert after a certain time
    setTimeout(() => {
        $(`#${uniqueId}`).alert('close');
    }, 2000); // Close the alert after 5 seconds
}

// Call the ajax polling for update every X milliseconds.
setInterval(updateDeviceValues, 1000);