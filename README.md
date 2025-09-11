# Hypridle Manager

A Python script to dynamically manage Hyprland's hypridle daemon configuration based on power status.

## Features

-   Different timeouts and actions for AC, battery, and low battery states.
-   Configurable timeouts and commands for dimming, locking, screen off (DPMS), and suspending.
-   Automatically updates `hypridle.conf` and restarts `hypridle` when power status changes.
-   Can manage `hypridle` as a systemd service.

## How it works

This script runs as a background daemon. It periodically checks the system's power status (connected to AC, on battery, or low battery). When the power status changes, it generates a new `~/.config/hypr/hypridle.conf` file with the timeouts and commands you've configured for that state. It then restarts the `hypridle` daemon to apply the new settings.

The generated `hypridle.conf` will use the `lock_command` you specify to lock the screen. It will also ensure that only one instance of the lock command is running at a time.

## Installation

### Using the Install Script (Recommended)

For a quick and easy setup, you can use the provided install script. This will handle all the necessary steps for you.

```bash
chmod +x install.sh
./install.sh
```

To install and configure the manager to run as a systemd service, use the `--systemd` flag:

```bash
./install.sh --systemd
```

If you prefer to install Python dependencies manually (e.g., via your distribution's package manager), you can skip the `pip install` step by using the `--skip-deps` flag:

```bash
./install.sh --skip-deps
```

### Manual Installation

If you prefer to install the script manually, follow these steps:

1.  **Install Python dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

    *Note: If `pip` is not available or you prefer to use your distribution's package manager, you may need to install `psutil` manually (e.g., `sudo apt install python3-psutil` on Debian/Ubuntu).*

## Configuration

1.  **Create the configuration directory:**

    ```bash
    mkdir -p ~/.config/hypridle-handler
    ```

2.  **Copy the example configuration:**

    ```bash
    cp config.ini.example ~/.config/hypridle-handler/config.ini
    ```

3.  **Edit the configuration:**

    Open `~/.config/hypridle-handler/config.ini` and customize the timeouts and commands for each power state.
    
        -   `systemd_mode`: Set to `true` to manage `hypridle` as a systemd service. Defaults to `false`.
        -   `low_battery_percentage`: The battery percentage at which to switch to the `low_battery` state.
        -   `hypridle_config_path`: The path to the `hypridle.conf` file to be generated. Defaults to `~/.config/hypr/hypridle.conf`.
        -   `lock_command`: The command to lock the screen. Defaults to `hyprlock`.
        -   `[on_ac]`, `[on_battery]`, `[low_battery]`: Sections for each power state.
        -   `*_timeout`: Timeouts in seconds for each action.
        -   `*_command`: Commands to be executed for each action.
    
    ## Hyprland Setup
    
    To start the `hypridle-manager.py` daemon with Hyprland, add the following to your `~/.config/hypr/hyprland.conf`:
    
    ```ini
    exec-once = hypridle-manager.py
    ```
    
    This will start the script in the background when you log in. It will then take care of managing the `hypridle` daemon for you.
    
    **Important:** Do NOT add `exec-once = hypridle` to your `hyprland.conf`. The `hypridle-manager.py` script will start and manage the `hypridle` process itself.
    
    ## Systemd Service (Optional)
    
    If you prefer to manage `hypridle` with systemd, the install script can set this up for you. Simply run:
    
    ```bash
    ./install.sh --systemd
    ```
    
    This will:
    1.  Set `systemd_mode = true` in `~/.config/hypridle-handler/config.ini`.
    2.  Create the necessary systemd service files (`hypridle.service` and `hypridle-manager.service`) in `~/.config/systemd/user/`.
    3.  Enable and start the `hypridle-manager.service`.
    
    If you prefer to set up systemd manually, follow these steps:
    
    1.  **Enable systemd mode in your config:**
    
        In `~/.config/hypridle-handler/config.ini`, set:
    
        ```ini
    systemd_mode = true
        ```
    
    2.  **Create a systemd service file for hypridle:**
    
        Create a file at `~/.config/systemd/user/hypridle.service`:
    
        ```ini
        [Unit]
        Description=Hyprland Idle Daemon
        PartOf=graphical-session.target
    
        [Service]
        ExecStart=/usr/bin/hypridle
        Restart=always
        RestartSec=1
    
        [Install]
        WantedBy=graphical-session.target
        ```
    
    3.  **Create a systemd service file for the manager:**
    
        Create a file at `~/.config/systemd/user/hypridle-manager.service`:
    
        ```ini
        [Unit]
        Description=Hypridle Power Manager
        PartOf=graphical-session.target
    
        [Service]
        ExecStart=/usr/local/bin/hypridle-manager.py
        Restart=always
        RestartSec=10
    
        [Install]
        WantedBy=graphical-session.target
        ```
    
    4.  **Enable and start the manager service:**
    
        ```bash
        systemctl --user enable --now hypridle-manager.service
        ```
    
        The manager will automatically enable and start the `hypridle.service` for you.
    
    When using systemd, you should **not** add `exec-once = hypridle-manager.py` or `exec-once = hypridle` to your `hyprland.conf`. The systemd services will manage the lifecycle of both the manager and the daemon.