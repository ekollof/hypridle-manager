# Hypridle Manager

A Python script to dynamically manage Hyprland's hypridle daemon configuration based on power status.

## Features

- **Real-time power monitoring**: Instantly detects power state changes using Linux udev events
- Different timeouts and actions for AC, battery, and low battery states
- Configurable timeouts and commands for dimming, locking, screen off (DPMS), and suspending
- Automatically updates `hypridle.conf` and restarts `hypridle` when power status changes
- Can manage `hypridle` as a systemd service
- **Lid switch handling**: Runs custom commands when the laptop lid is closed, based on power state
- Low resource usage with event-driven architecture

## How it works

This script runs as a background daemon that monitors your system's power status in real-time. Using Linux's udev system, it instantly detects when you plug or unplug your charger and immediately updates power profiles. When the power status changes, it generates a new `~/.config/hypr/hypridle.conf` file with the timeouts and commands you've configured for that state and restarts the `hypridle` daemon to apply the new settings.

The generated `hypridle.conf` will use the `lock_command` you specify to lock the screen. It will also ensure that only one instance of the lock command is running at a time.

## Installation

### Using the Python Installer (Recommended)

For a quick and easy setup, use the provided Python installer. This will handle all necessary steps including dependency installation, script setup, and configuration.

```bash
python3 install.py
```

To install and configure the manager to run as a systemd service, use the `--systemd` flag:

```bash
python3 install.py --systemd
```

If you prefer to install Python dependencies manually (e.g., via your distribution's package manager), you can skip the `pip install` step by using the `--skip-deps` flag:

```bash
python3 install.py --skip-deps
```

The installer will:

- Install Python dependencies (unless `--skip-deps` is used)
- Install the scripts to `/usr/local/bin`
- Create the configuration directory and copy the example config
- **Automatically add lid switch configuration** to your config file
- Optionally set up systemd services and update Hyprland configuration

### Manual Installation

If you prefer to install manually, follow these steps:

1. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   *Note: If `pip` is not available or you prefer to use your distribution's package manager, you may need to install the dependencies manually:*
   - *`sudo apt install python3-psutil python3-pyudev` on Debian/Ubuntu*
   - *`sudo pacman -S python-psutil python-pyudev` on Arch Linux*
   - *`sudo dnf install python3-psutil python3-pyudev` on Fedora*

## Configuration

1. Create the configuration directory:

   ```bash
   mkdir -p ~/.config/hypridle-handler
   ```

2. Copy the example configuration:

   ```bash
   cp config.ini.example ~/.config/hypridle-handler/config.ini
   ```

3. Edit the configuration:

   Open `~/.config/hypridle-handler/config.ini` and customize the timeouts and commands for each power state.

   - `systemd_mode`: Set to `true` to manage `hypridle` as a systemd service. Defaults to `false`.
   - `low_battery_percentage`: The battery percentage at which to switch to the `low_battery` state.
   - `hypridle_config_path`: The path to the `hypridle.conf` file to be generated. Defaults to `~/.config/hypr/hypridle.conf`.
   - `lock_command`: The command to lock the screen. Defaults to `hyprlock`.
   - `[on_ac]`, `[on_battery]`, `[low_battery]`: Sections for each power state.
   - `*_timeout`: Timeouts in seconds for each action.
   - `*_command`: Commands to be executed for each action.
   - `dim_resume_command`: Command to restore brightness when resuming from dim (should reverse the dim_command).

## Lid Switch Handling

The `hyprland-lid-manager.py` script handles laptop lid switch events. When the lid is closed, it checks the current power state and runs the appropriate command from the `[lid_switch]` section.

To enable lid switch handling in Hyprland, add the following to your `~/.config/hypr/hyprland.conf`:

```ini
bindl=,switch:Lid Switch,exec,hyprland-lid-manager.py
```

This will run the lid manager script whenever the lid is closed. The script will determine the power state and execute the configured command (e.g., lock session, hibernate, etc.).

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
python3 install.py --systemd
```

This will:

1. Set `systemd_mode = true` in `~/.config/hypridle-handler/config.ini`.
2. Create the necessary systemd service files (`hypridle.service` and `hypridle-manager.service`) in `~/.config/systemd/user/`.
3. Enable and start the `hypridle-manager.service`.
4. Automatically detect and comment out conflicting Hyprland configuration entries.

If you prefer to set up systemd manually, follow these steps:

1. Enable systemd mode in your config:

   In `~/.config/hypridle-handler/config.ini`, set:

   ```ini
   systemd_mode = true
   ```

2. Create a systemd service file for hypridle:

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

3. Create a systemd service file for the manager:

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

4. Enable and start the manager service:

   ```bash
   systemctl --user enable --now hypridle-manager.service
   ```

   The manager will automatically enable and start the `hypridle.service` for you.

When using systemd, you should **not** add `exec-once = hypridle-manager.py` or `exec-once = hypridle` to your `hyprland.conf`. The systemd services will manage the lifecycle of both the manager and the daemon.
