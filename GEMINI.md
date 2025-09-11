# Project: Hypridle Power Manager

This project contains a Python script that acts as a power management daemon for Hyprland's `hypridle`.

## Current Status

I have created a set of files to provide dynamic power management for `hypridle` based on the device's power status.

### File Structure

-   `hypridle-manager.py`: The main Python script that runs as a daemon.
-   `config.ini.example`: An example configuration file (INI format).
-   `requirements.txt`: A file listing the Python dependencies.
-   `README.md`: A file with detailed setup and usage instructions.
-   `install.sh`: A convenient script to automate the installation process.

### Functionality

The `hypridle-manager.py` script provides real-time monitoring of power status (AC, battery, low battery) using Linux's udev event system and dynamically generates the `hypridle.conf` file. This allows for different timeouts for dimming, locking, and suspending based on the power source with instant response to power state changes.

It now uses **INI files** for configuration, leveraging Python's built-in `configparser` module, eliminating the need for external TOML dependencies.

It also includes the following features:

-   **Real-time Power Monitoring:** Uses Linux udev events to instantly detect power state changes instead of polling every 30 seconds, providing immediate response and lower resource usage.
-   **Systemd Integration:** The script can be run as a systemd service and can manage the `hypridle` service itself. The `install.sh` script provides a `--systemd` option for easy setup of systemd services.
-   **Templated Lock Command:** The lock command is now templated from the configuration file, and the script ensures that only one instance of the lock command is running at a time.
-   **Simplified Installation:** The `install.sh` script automates the setup, including dependency installation (with a `--skip-deps` option for environments with system-managed Python packages), script placement, and configuration file setup.
-   **Event-driven Architecture:** Low CPU usage with efficient event-based monitoring instead of continuous polling.

## Next Steps

The user can now use the `install.sh` script to set up and configure the `hypridle-manager`. Detailed instructions are available in `README.md`.