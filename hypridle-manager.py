#!/usr/bin/env python

import configparser
import contextlib
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil
import pyudev

if platform.system() != "Linux":
    print("This script is designed for Linux systems.", file=sys.stderr)
    sys.exit(1)

CONFIG_PATH = Path.home() / ".config/hypridle-handler/config.ini"

def send_notification(message: str, timeout: int = 5000) -> None:
    """
    @brief Sends a desktop notification.
    @param message The notification message.
    @param timeout The notification timeout in milliseconds.
    """
    try:
        subprocess.run(["notify-send", "-t", str(timeout), "Hypridle Manager", message], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to send notification: {e}", file=sys.stderr)

def get_power_status(config: configparser.ConfigParser) -> str:
    """
    @brief Gets the current power status.
    @param config The configuration parser.
    @return The power status string.
    """
    battery = psutil.sensors_battery()
    if battery is None:
        return "on_ac"

    if battery.power_plugged:
        return "on_ac"

    low_battery_percentage = config.getint('general', 'low_battery_percentage', fallback=20)
    if battery.percent <= low_battery_percentage:
        return "low_battery"

    return "on_battery"

def generate_hypridle_config(power_state: str, config: configparser.ConfigParser) -> str:
    """
    @brief Generates the hypridle.conf content.
    @param power_state The current power state.
    @param config The configuration parser.
    @return The generated config content.
    """
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
        dim_resume_command = config.get(power_state, 'dim_resume_command', fallback='')
        config_content += f"""

listener {{
    timeout = {dim_timeout}
    on-timeout = {dim_command}"""
        if dim_resume_command:
            config_content += f"""
    on-resume = {dim_resume_command}"""
        config_content += f"""
}}"""

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

def restart_hypridle(systemd_mode: bool = False) -> None:
    """
    @brief Restarts the hypridle daemon.
    @param systemd_mode Whether to use systemd mode.
    @throws subprocess.CalledProcessError If restarting fails.
    """
    if systemd_mode:
        try:
            subprocess.run(["systemctl", "--user", "restart", "hypridle.service"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error restarting hypridle service: {e}", file=sys.stderr)
    else:
        with contextlib.suppress(subprocess.CalledProcessError):
            subprocess.run(["pkill", "hypridle"], check=True)
        # Wait a moment for the process to terminate
        time.sleep(1)
        subprocess.Popen(["hypridle"], start_new_session=True)

def check_and_enable_hypridle_service() -> None:
    """
    @brief Checks if the hypridle service is enabled and enables it if not.
    @throws subprocess.CalledProcessError If managing the service fails.
    """
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

def handle_power_change(config: configparser.ConfigParser, systemd_mode: bool, hypridle_config_path: Path, current_power_state: list[str | None], enable_notifications: bool, notification_timeout: int) -> None:
    """
    @brief Handle power state change and update configuration.
    @param config The configuration parser.
    @param systemd_mode Whether to use systemd mode.
    @param hypridle_config_path The path to the hypridle config file.
    @param current_power_state The mutable list holding the current power state.
    @param enable_notifications Whether to send notifications.
    @param notification_timeout The notification timeout in milliseconds.
    """
    new_power_state = get_power_status(config)

    if new_power_state != current_power_state[0]:
        print(f"Power state changed to: {new_power_state}")
        current_power_state[0] = new_power_state

        if enable_notifications:
            message = f"Power state changed to {new_power_state.replace('_', ' ').title()}"
            send_notification(message, notification_timeout)

        hypridle_config_content = generate_hypridle_config(current_power_state[0], config)

        with open(hypridle_config_path, "w") as f:
            f.write(hypridle_config_content)

        print("hypridle.conf updated. Restarting hypridle...")
        restart_hypridle(systemd_mode)

def monitor_power_events(config: configparser.ConfigParser, systemd_mode: bool, hypridle_config_path: Path, current_power_state: list[str | None], enable_notifications: bool, notification_timeout: int) -> None:
    """
    @brief Monitor power supply events using udev.
    @param config The configuration parser.
    @param systemd_mode Whether to use systemd mode.
    @param hypridle_config_path The path to the hypridle config file.
    @param current_power_state The mutable list holding the current power state.
    @param enable_notifications Whether to send notifications.
    @param notification_timeout The notification timeout in milliseconds.
    """
    context = pyudev.Context() # type: ignore
    monitor = pyudev.Monitor.from_netlink(context) # type: ignore
    monitor.filter_by('power_supply')

    print("Starting real-time power monitoring...")

    for device in iter(monitor.poll, None):
        if device.action in ['change', 'add', 'remove']:
            # Small delay to let the system settle after the event
            time.sleep(0.5)
            handle_power_change(config, systemd_mode, hypridle_config_path, current_power_state, enable_notifications, notification_timeout)

def main() -> None:
    """
    @brief Main function.
    """
    if not CONFIG_PATH.is_file():
        print(f"Error: Configuration file not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    config = configparser.ConfigParser(interpolation=None)
    try:
        config.read(CONFIG_PATH)
    except configparser.Error as e:
        print(f"Error: Invalid INI in {CONFIG_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

    systemd_mode = config.getboolean('general', 'systemd_mode', fallback=False)
    enable_notifications = config.getboolean('general', 'enable_notifications', fallback=True)
    notification_timeout = config.getint('general', 'notification_timeout', fallback=5000)

    if systemd_mode:
        check_and_enable_hypridle_service()

    hypridle_config_path = Path(config.get('general', 'hypridle_config_path', fallback='/tmp/hypridle.conf')).expanduser()

    # Use a list to make it mutable for the callback
    current_power_state: list[str | None] = [None]

    # Set initial state
    handle_power_change(config, systemd_mode, hypridle_config_path, current_power_state, enable_notifications, notification_timeout)

    # Start monitoring in a separate thread so we can handle interrupts
    monitor_thread = threading.Thread(
        target=monitor_power_events,
        args=(config, systemd_mode, hypridle_config_path, current_power_state, enable_notifications, notification_timeout),
        daemon=True
    )
    monitor_thread.start()

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down power manager...")
        sys.exit(0)

if __name__ == "__main__":
    main()
