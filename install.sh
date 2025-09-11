#!/bin/bash

# Exit on error
set -e

SYSTEMD_MODE=false
SKIP_DEPS=false
VENV_INSTALL=false

# Function to show help
show_help() {
    cat << EOF
Hypridle Manager Installer

Usage: $0 [OPTIONS]

Options:
    --systemd       Enable systemd mode and create systemd services
    --skip-deps     Skip Python dependency installation (use if dependencies 
                   are already installed via system package manager)
    --help, -h      Show this help message

Examples:
    $0                    # Basic installation
    $0 --systemd         # Install with systemd service setup
    $0 --skip-deps       # Install without installing Python dependencies
    $0 --systemd --skip-deps  # Both systemd mode and skip deps

For more information, see README.md
EOF
}

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
    --help|-h)
        show_help
        exit 0
        ;;
    *)
        echo "Unknown option: $arg"
        echo "Use --help for usage information"
        exit 1
        ;;
    esac
done

# Check for Python 3
if ! command -v python3 &>/dev/null; then
    echo "Error: Python 3 is required but not found. Please install it and try again."
    exit 1
fi

if [ "$SKIP_DEPS" = false ]; then
    echo "Checking for Python dependencies..."
    
    # Check if dependencies are already available via system packages
    echo "Checking if dependencies are already installed..."
    python3 -c "import psutil, pyudev" &>/dev/null
    DEPS_AVAILABLE=$?
    
    if [ $DEPS_AVAILABLE -eq 0 ]; then
        echo "All dependencies are already available. Skipping installation."
    else
        echo "Dependencies not found. Attempting to install..."
        
        # First try pip3 if available
        if command -v pip3 &>/dev/null; then
            echo "Attempting to install Python dependencies using pip3..."
            
            # Try pip install, capture specific PEP 668 error
            pip3 install -r requirements.txt 2>&1 | tee /tmp/pip_install.log
            
            if [ ${PIPESTATUS[0]} -eq 0 ]; then
                echo "Successfully installed dependencies using pip3."
            else
                # Check if it's a PEP 668 externally-managed-environment error
                if grep -q "externally-managed-environment\|error: externally-managed-environment" /tmp/pip_install.log; then
                    echo "PEP 668 externally-managed-environment detected."
                    echo "Attempting alternative installation methods..."
                    
                    # Try pipx if available (though it's not ideal for libraries)
                    if command -v pipx &>/dev/null; then
                        echo "pipx detected, but it's not suitable for installing libraries."
                        echo "Skipping pipx and trying virtual environment..."
                    fi
                    
                    # Try virtual environment approach
                    echo "Trying virtual environment approach..."
                    python3 -m venv ~/.local/share/hypridle-manager-venv --system-site-packages || {
                        echo "Failed to create virtual environment."
                    }
                    
                    if [ -f ~/.local/share/hypridle-manager-venv/bin/activate ]; then
                        source ~/.local/share/hypridle-manager-venv/bin/activate
                        pip install -r requirements.txt && {
                            echo "Successfully installed dependencies in virtual environment."
                            # Update the shebang to use the virtual environment Python
                            sed -i '1s|#!/usr/bin/env python3|#!~/.local/share/hypridle-manager-venv/bin/python3|' hypridle-manager.py
                            VENV_INSTALL=true
                        } || {
                            deactivate 2>/dev/null || true
                            echo "Virtual environment installation failed."
                        }
                        deactivate 2>/dev/null || true
                    fi
                    
                    # Check if virtual environment installation succeeded
                    if [ "$VENV_INSTALL" != "true" ]; then
                        echo ""
                        echo "All pip-based installation methods failed due to PEP 668."
                        echo "Please install dependencies using your system package manager:"
                        echo ""
                        echo "For Debian/Ubuntu:"
                        echo "  sudo apt install python3-psutil python3-pyudev"
                        echo ""
                        echo "For Arch Linux:"
                        echo "  sudo pacman -S python-psutil python-pyudev"
                        echo ""
                        echo "For Fedora:"
                        echo "  sudo dnf install python3-psutil python3-pyudev"
                        echo ""
                        echo "For openSUSE:"
                        echo "  sudo zypper install python3-psutil python3-pyudev"
                        echo ""
                        echo "After installing system packages, re-run this script with --skip-deps"
                        exit 1
                    fi
                else
                    echo "pip3 installation failed for other reasons. Please check the error above."
                    exit 1
                fi
            fi
            
            # Clean up temp file
            rm -f /tmp/pip_install.log
        else
            echo "pip3 not found. Attempting to install using ensurepip..."
            python3 -m ensurepip --default-pip || {
                echo "Failed to ensure pip3 is installed."
                echo "Please install dependencies using your system package manager:"
                echo "  sudo apt install python3-psutil python3-pyudev  # Debian/Ubuntu"
                echo "  sudo pacman -S python-psutil python-pyudev     # Arch Linux" 
                echo "  sudo dnf install python3-psutil python3-pyudev  # Fedora"
                echo "Then re-run this script with --skip-deps"
                exit 1
            }
        fi
    fi
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
    sudo cp hypridle-manager.py /usr/local/bin/
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

    echo "Checking hyprland configuration for conflicting exec-once entries..."
    HYPRLAND_CONFIG="${HOME}/.config/hypr/hyprland.conf"
    CONFIG_UPDATED=false
    
    if [ -f "$HYPRLAND_CONFIG" ]; then
        # Check for hypridle exec-once entries and comment them out
        if grep -q "^[[:space:]]*exec-once[[:space:]]*=.*hypridle" "$HYPRLAND_CONFIG"; then
            echo "Found hypridle exec-once entries in hyprland.conf. Commenting them out..."
            sed -i 's/^[[:space:]]*exec-once[[:space:]]*=.*hypridle/# &/' "$HYPRLAND_CONFIG"
            CONFIG_UPDATED=true
        fi
        
        # Check for hypridle-manager exec-once entries and comment them out
        if grep -q "^[[:space:]]*exec-once[[:space:]]*=.*hypridle-manager" "$HYPRLAND_CONFIG"; then
            echo "Found hypridle-manager exec-once entries in hyprland.conf. Commenting them out..."
            sed -i 's/^[[:space:]]*exec-once[[:space:]]*=.*hypridle-manager/# &/' "$HYPRLAND_CONFIG"
            CONFIG_UPDATED=true
        fi
        
        if [ "$CONFIG_UPDATED" = true ]; then
            echo "Updated hyprland.conf - commented out conflicting exec-once entries."
            echo "These services will now be managed by systemd instead."
        else
            echo "No conflicting exec-once entries found in hyprland.conf."
        fi
    else
        echo "Warning: hyprland.conf not found at $HYPRLAND_CONFIG"
        echo "Make sure you don't have exec-once entries for hypridle or hypridle-manager."
    fi

    echo "Creating systemd service files..."
    mkdir -p ~/.config/systemd/user/

    # hypridle.service
    cat <<EOF >~/.config/systemd/user/hypridle.service
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
    cat <<EOF >~/.config/systemd/user/hypridle-manager.service
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
    systemctl --user enable --now hypridle-manager.service || {
        echo "Error: Failed to enable/start hypridle-manager.service. Please check systemd logs."
        exit 1
    }
    echo "hypridle-manager.service enabled and started."
    
    echo ""
    echo "Systemd setup complete!"
    echo "The hypridle-manager and hypridle services are now managed by systemd."
    if [ "$CONFIG_UPDATED" = true ]; then
        echo "Your hyprland.conf has been updated to remove conflicting exec-once entries."
        echo "You can review the changes at: $HYPRLAND_CONFIG"
    fi
    echo "You can check service status with:"
    echo "  systemctl --user status hypridle-manager.service"
    echo "  systemctl --user status hypridle.service"
else
    echo -e "\nInstallation complete!"
    echo "Please edit ~/.config/hypridle-handler/config.ini to your liking."
    
    if [ "$VENV_INSTALL" = "true" ]; then
        echo ""
        echo "Note: Dependencies were installed in a virtual environment due to PEP 668."
        echo "The script has been configured to use the virtual environment automatically."
        echo ""
    fi
    
    echo "After configuration, you can add 'exec-once = hypridle-manager.py' to your hyprland.conf"
    echo "or set up the systemd service as described in the README."
fi

echo "Installation finished."
