#!/usr/bin/env python

import configparser
import platform
import subprocess
import sys
from pathlib import Path

import psutil

if platform.system() != "Linux":
    print("This script is designed for Linux systems.", file=sys.stderr)
    sys.exit(1)

CONFIG_PATH = Path.home() / ".config/hypridle-handler/config.ini"

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

def get_lid_command(power_state: str, config: configparser.ConfigParser) -> str | None:
    """
    @brief Gets the lid command for the current power state.
    @param power_state The current power state.
    @param config The configuration parser.
    @return The command string or None if not set.
    """
    command = config.get('lid_switch', f'{power_state}_command', fallback='')
    return command.strip() if command.strip() else None

def main() -> None:
    """
    @brief Main function for lid switch handling.
    """
    if not CONFIG_PATH.is_file():
        print(f"Error: Configuration file not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_PATH)
    except configparser.Error as e:
        print(f"Error: Invalid INI in {CONFIG_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

    power_state = get_power_status(config)
    command = get_lid_command(power_state, config)

    if command:
        print(f"Lid closed on {power_state}, running: {command}")
        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running lid command: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Lid closed on {power_state}, no command configured.")

if __name__ == "__main__":
    main()
