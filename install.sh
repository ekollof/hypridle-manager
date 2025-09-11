#!/bin/bash

# Exit on error
set -e

SYSTEMD_MODE=false
SKIP_DEPS=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --systemd)
        SYSTEMD_MODE=true
        shift
        ;;
        --skip-deps)
        SKIP_DEPS=true
        shift
        ;;
        *)
        # Unknown option
        ;;
    esac
done

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found. Please install it and try again."
    exit 1
fi

if [ "$SKIP_DEPS" = false ]; then
    echo "Checking for Python dependencies..."
    if ! command -v pip3 &> /dev/null; then
        echo "Warning: pip3 not found. Attempting to install Python dependencies using 'python3 -m ensurepip'. If this fails, you may need to install 'python3-pip' or equivalent for your distribution."
        python3 -m ensurepip --default-pip || { echo "Error: Failed to ensure pip3 is installed. Please install pip3 manually (e.g., 'sudo apt install python3-pip' or 'sudo pacman -S python-pip') and try again, or install 'psutil' via your distribution's package manager and run with --skip-deps."; exit 1; }
    fi

    echo "Installing Python dependencies using pip3..."
    # Attempt to install psutil. If it fails due to externally-managed-environment,
    # the user will need to install it via their system's package manager.
    pip3 install -r requirements.txt || {
        echo "Error: Failed to install Python dependencies with pip3. This might be due to an 'externally-managed-environment'."
        echo "Please install 'psutil' manually using your distribution's package manager (e.g., 'sudo apt install python3-psutil' or 'sudo pacman -S python-psutil') and then re-run this script with the '--skip-deps' flag."
        exit 1
    }
else
    echo "Skipping Python dependency installation as requested."
fi

echo "Making the script executable..."
chmod +x hypridle-manager.py

echo "Installing the script to /usr/local/bin..."
if [ -w /usr/local/bin ]; then
    mv hypridle-manager.py /usr/local/bin/
else
    echo "Cannot write to /usr/local/bin. Trying with sudo."
    sudo mv hypridle-manager.py /usr/local/bin/
fi

echo "Creating configuration directory..."
mkdir -p ~/.config/hypridle-handler

CONFIG_FILE=~/.config/hypridle-handler/config.ini

echo "Copying example configuration..."
cp config.ini.example "$CONFIG_FILE"

if [ "$SYSTEMD_MODE" = true ]; then
    echo "Configuring for systemd mode..."
    # Set systemd_mode = true in config.ini
    sed -i 's/systemd_mode = false/systemd_mode = true/' "$CONFIG_FILE"

    echo "Creating systemd service files..."
    mkdir -p ~/.config/systemd/user/

    # hypridle.service
    cat << EOF > ~/.config/systemd/user/hypridle.service
[Unit]
Description=Hyprland Idle Daemon
PartOf=graphical-session.target

[Service]
ExecStart=/usr/bin/hypridle
Restart=always
RestartSec=1

[Install]
WantedBy=graphical-session.target
EOF

    # hypridle-manager.service
    cat << EOF > ~/.config/systemd/user/hypridle-manager.service
[Unit]
Description=Hypridle Power Manager
PartOf=graphical-session.target

[Service]
ExecStart=/usr/local/bin/hypridle-manager.py
Restart=always
RestartSec=10

[Install]
WantedBy=graphical-session.target
EOF

    echo "Enabling and starting hypridle-manager.service..."
    systemctl --user daemon-reload
    systemctl --user enable --now hypridle-manager.service || { echo "Error: Failed to enable/start hypridle-manager.service. Please check systemd logs."; exit 1; }
    echo "hypridle-manager.service enabled and started."
else
    echo -e "\nInstallation complete!"
    echo "Please edit ~/.config/hypridle-handler/config.ini to your liking."
    echo "After that, you can add 'exec-once = hypridle-manager.py' to your hyprland.conf"
    echo "or set up the systemd service as described in the README."
fi

echo "Installation finished."
