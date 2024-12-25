import sys
sys.path.insert(0, "/opt/clay/clay_golem")
import sqlite3
import matplotlib
# matplotlib.use("TkAgg")  # Use TkAgg backend for interactive plotting
import matplotlib.pyplot as plt

from datetime import datetime


def infer_unit_from_table_name(table_name):
    if "_temp" in table_name:
        return "°C"
    if "device_temp" in table_name:
        return "°C"
    if "pwm" in table_name:
        return "PWM, %"
    elif "_hum" in table_name:
        return "%"
    elif "_state" in table_name:
        return "state"
    elif "co2" in table_name:
        return "PPM CO2"
    return "Value"

def fetch_and_plot_data(db_name, tables, start_datetime, end_datetime):
    """
    Fetch data from specified tables in the SQLite database and plot them as subplots.

    :param db_name: Name of the SQLite database file.
    :param tables: List of table names to fetch data from.
    :param start_datetime: Start datetime (string in format "DD-MM-YYYY HH:MM:SS").
    :param end_datetime: End datetime (string in format "DD-MM-YYYY HH:MM:SS").
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    color_map = plt.get_cmap('tab10')  # Color map for distinct plot colors
    num_subplots = len(tables)
    fig, axes = plt.subplots(num_subplots, 1, figsize=(10, 5 * num_subplots), sharex=True)
    if num_subplots == 1:
        axes = [axes]  # Ensure axes is iterable for a single subplot case

    name_str = f"System statistics for {start_datetime} - {end_datetime}"
    start_dt = datetime.strptime(start_datetime, "%d-%m-%Y %H:%M:%S")
    end_dt = datetime.strptime(end_datetime, "%d-%m-%Y %H:%M:%S")

    for idx, table_name in enumerate(tables):
        try:
            cursor.execute(f"""
                SELECT datetime, value FROM {table_name}
                WHERE datetime >= ? AND datetime <= ?
                ORDER BY datetime
            """, (start_datetime, end_datetime))
            rows = cursor.fetchall()
            if rows:
                times, values = zip(*[(datetime.strptime(row[0], "%d-%m-%Y %H:%M:%S"), row[1]) for row in rows])
                ax = axes[idx]
                unit = infer_unit_from_table_name(table_name)
                ax.plot(times, values, '-o', label=f"device_{table_name.split('_')[1]} ({unit})", color=color_map(idx % 10))
                ax.set_ylabel(unit)
                ax.legend(loc="upper left")
                ax.grid(True)
            else:
                axes[idx].text(0.5, 0.5, f"No data for {table_name}", ha='center', va='center', fontsize=12)
        except sqlite3.OperationalError:
            print(f"Table '{table_name}' does not exist. Skipping.")
            continue

    axes[-1].set_xlabel("Datetime")
    # plt.tight_layout()
    fig.suptitle(name_str)
    plt.show()
    conn.close()


def show_all_tables(db_name):
    """
    Fetch all table names from the SQLite database.

    :param db_name: Name of the SQLite database file.
    :return: List of table names.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name FROM sqlite_master WHERE type='table';
    """)
    tables = [row[0] for row in cursor.fetchall()]

    conn.close()
    return tables


if __name__ == "__main__":
    # Example usage
    db_name = "/opt/clay/clay_golem/instance/data.sqlite"
    start_datetime = "25-12-2024 00:00:00"
    end_datetime = "25-12-2024 23:59:59"
    # tables = ['device_100_red_pwm_2', 'device_100_white_pwm_2', 'device_101_state', 'device_102_state',
    #           'device_103_state', 'device_104_state']
    # exp_tables = ['device_110_state', 'device_111_state', 'device_112_state', 'device_113_state', 'device_106_hum', 'device_107_temp', 'device_108_hum', 'device_109_temp']
    exp_tables = ['device_99_co2','device_110_state',# 'device_111_state', #'device_112_state', 'device_113_state',
                  #'device_106_hum','device_107_temp',
                  'device_108_hum',# 'device_109_temp'
                  ]

    control_tables =  ['device_118_state', 'device_119_state', 'device_120_state', 'device_121_state', 'device_122_temp',
                       'device_123_hum', 'device_124_temp']
    # tables = [ 'device_101_state', 'device_102_state', 'device_103_state', 'device_104_state']
    # Fetch data and plot
    # data = fetch_data_for_plot(db_name, device_ids, start_datetime, end_datetime)
    # plot_data(data, device_ids)
    print(show_all_tables(db_name))
    fetch_and_plot_data(db_name, exp_tables, start_datetime, end_datetime)
    fetch_and_plot_data(db_name, control_tables, start_datetime, end_datetime)

