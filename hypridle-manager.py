#!/usr/bin/env python

import sys
import time
from pathlib import Path
import configparser
import psutil
import subprocess

CONFIG_PATH = Path.home() / ".config/hypridle-handler/config.ini"

def get_power_status(config):
    """Gets the current power status."""
    battery = psutil.sensors_battery()
    if battery is None:
        return "on_ac"

    if battery.power_plugged:
        return "on_ac"

    low_battery_percentage = config.getint('general', 'low_battery_percentage', fallback=20)
    if battery.percent <= low_battery_percentage:
        return "low_battery"

    return "on_battery"

def generate_hypridle_config(power_state, config):
    """Generates the hypridle.conf content."""
    lock_command = config.get('general', 'lock_command', fallback='hyprlock')
    
    # Get the dpms_on_command from the current state, or default to a safe value
    dpms_on_command = config.get(power_state, 'dpms_on_command', fallback='hyprctl dispatch dpms on')

    config_content = f"""
general {{
    lock_cmd = pidof {lock_command} || {lock_command}
    before_sleep_cmd = loginctl lock-session
    after_sleep_cmd = {dpms_on_command}
}}
"""

    dim_timeout = config.getint(power_state, 'dim_timeout', fallback=0)
    if dim_timeout > 0:
        dim_command = config.get(power_state, 'dim_command')
        config_content += f"""

listener {{
    timeout = {dim_timeout}
    on-timeout = {dim_command}
}}
"""

    lock_timeout = config.getint(power_state, 'lock_timeout', fallback=0)
    if lock_timeout > 0:
        config_content += f"""

listener {{
    timeout = {lock_timeout}
    on-timeout = {lock_command}
}}
"""

    dpms_off_timeout = config.getint(power_state, 'dpms_off_timeout', fallback=0)
    if dpms_off_timeout > 0:
        dpms_off_command = config.get(power_state, 'dpms_off_command')
        config_content += f"""

listener {{
    timeout = {dpms_off_timeout}
    on-timeout = {dpms_off_command}
    on-resume = {dpms_on_command}
}}
"""

    suspend_timeout = config.getint(power_state, 'suspend_timeout', fallback=0)
    if suspend_timeout > 0:
        suspend_command = config.get(power_state, 'suspend_command')
        config_content += f"""

listener {{
    timeout = {suspend_timeout}
    on-timeout = {suspend_command}
}}
"""
    return config_content

def restart_hypridle(systemd_mode=False):
    """Restarts the hypridle daemon."""
    if systemd_mode:
        try:
            subprocess.run(["systemctl", "--user", "restart", "hypridle.service"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error restarting hypridle service: {e}", file=sys.stderr)
    else:
        try:
            subprocess.run(["pkill", "hypridle"], check=True)
        except subprocess.CalledProcessError:
            # hypridle might not be running, which is fine
            pass
        # Wait a moment for the process to terminate
        time.sleep(1)
        subprocess.Popen(["hypridle"], start_new_session=True)

def check_and_enable_hypridle_service():
    """Checks if the hypridle service is enabled and enables it if not."""
    try:
        # Check if the service is enabled
        status_process = subprocess.run(["systemctl", "--user", "is-enabled", "hypridle.service"], capture_output=True, text=True)
        
        # If the service is not enabled, enable it
        if status_process.stdout.strip() != "enabled":
            print("hypridle.service is not enabled. Enabling it now...")
            subprocess.run(["systemctl", "--user", "enable", "--now", "hypridle.service"], check=True)
            print("hypridle.service enabled successfully.")
            
    except subprocess.CalledProcessError as e:
        print(f"Error managing hypridle service: {e}", file=sys.stderr)

def main():
    """Main function."""
    if not CONFIG_PATH.is_file():
        print(f"Error: Configuration file not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_PATH)
    except configparser.Error as e:
        print(f"Error: Invalid INI in {CONFIG_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

    systemd_mode = config.getboolean('general', 'systemd_mode', fallback=False)
    
    if systemd_mode:
        check_and_enable_hypridle_service()
        
    hypridle_config_path = Path(config.get('general', 'hypridle_config_path', fallback='/tmp/hypridle.conf')).expanduser()

    current_power_state = None

    while True:
        new_power_state = get_power_status(config)

        if new_power_state != current_power_state:
            print(f"Power state changed to: {new_power_state}")
            current_power_state = new_power_state
            
            hypridle_config_content = generate_hypridle_config(current_power_state, config)
            
            with open(hypridle_config_path, "w") as f:
                f.write(hypridle_config_content)
            
            print("hypridle.conf updated. Restarting hypridle...")
            restart_hypridle(systemd_mode)

        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    main()
