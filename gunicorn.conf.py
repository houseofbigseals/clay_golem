import os
import socket
import subprocess


def get_ip_address(ifname):
    """Get the current IP address of the given interface."""
    try:
        ip_address = subprocess.check_output(f"ip -o -4 addr list {ifname} | awk '{{print $4}}' | cut -d/ -f1", shell=True).decode().strip()
        return ip_address
    except subprocess.CalledProcessError:
        print(f"Could not get IP address for interface {ifname}")
        return '0.0.0.0'  # Default to this IP if something goes wrong


# Find the directory of the current configuration file
config_dir = os.path.dirname(os.path.abspath(__file__))

# Assuming your Flask app and virtual environment are relative to this config's location
# Update these paths according to your project structure
app_dir = config_dir  #os.path.join(config_dir)
venv_path = os.path.join(config_dir, 'venv')

# Automatically find the IP address of the wg0 interface
ip_address = get_ip_address('wg0')
print(ip_address)
print(venv_path)
print(app_dir)
# Bind gunicorn to the IP address of wg0 interface on port 8000
bind = f"{ip_address}:8000"

# Specify the number of workers
workers = 4

# Set the working directory to the directory of your Flask application
chdir = app_dir

# Specify how to load the app. Adjust this import to match how your Flask app is structured
# For example, if your Flask factory function is named create_app and is located in
# a file named flaskr.py within the specified app_dir
wsgi_app = 'flaskr:create_app()'

# # Logging configuration
# accesslog = '-'  # Log to stdout
# errorlog = '-'  # Log to stderr

# You can add more gunicorn configuration options as needed
max_requests = 1000         # gracefully restart a worker after 1000 requests
max_requests_jitter = 50    # add random jitter up to 50 requests