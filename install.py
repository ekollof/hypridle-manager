#!/usr/bin/env python3

import argparse
import configparser
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], check: bool = True):
    """Run a command and return the result."""
    return subprocess.run(cmd, check=check, capture_output=True, text=True)

def check_python() -> None:
    """Check if Python 3 is available."""
    try:
        result = run_command([sys.executable, "--version"])
        if "Python 3" not in result.stdout:
            print("Error: Python 3 is required.")
            sys.exit(1)
    except subprocess.CalledProcessError:
        print("Error: Python 3 is required but not found.")
        sys.exit(1)

def install_dependencies(skip_deps: bool, venv_path: Path) -> bool:
    """Install Python dependencies. Returns True if venv was used."""
    if skip_deps:
        print("Skipping Python dependency installation as requested.")
        return False

    print("Checking for Python dependencies...")

    # Check if dependencies are available
    if importlib.util.find_spec("psutil") and importlib.util.find_spec("pyudev"):
        print("All dependencies are already available.")
        return False

    print("Dependencies not found. Attempting to install...")

    # Try pip install
    try:
        run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Successfully installed dependencies using pip.")
        return False
    except subprocess.CalledProcessError as e:
        if "externally-managed-environment" in e.stderr:
            print("PEP 668 externally-managed-environment detected.")
            print("Trying virtual environment approach...")

            # Create venv
            venv_path.mkdir(parents=True, exist_ok=True)
            run_command([sys.executable, "-m", "venv", str(venv_path), "--system-site-packages"])

            # Install in venv
            pip_path = venv_path / "bin" / "pip"
            run_command([str(pip_path), "install", "-r", "requirements.txt"])

            print("Successfully installed dependencies in virtual environment.")
            return True
        else:
            print("pip installation failed.")
            check_system_deps()
            return False

def check_system_deps() -> None:
    """Check if dependencies are available via system packages."""
    if importlib.util.find_spec("psutil") and importlib.util.find_spec("pyudev"):
        print("Dependencies are available via system packages.")
    else:
        print("Dependencies are not available. Please install them using your system package manager:")
        print("For Debian/Ubuntu: sudo apt install python3-psutil python3-pyudev")
        print("For Arch Linux: sudo pacman -S python-psutil python-pyudev")
        print("For Fedora: sudo dnf install python3-psutil python3-pyudev")
        print("For openSUSE: sudo zypper install python3-psutil python3-pyudev")
        print("Then re-run this script with --skip-deps")
        sys.exit(1)

def install_scripts(venv_path: Path, venv_used: bool) -> None:
    """Install the scripts to /usr/local/bin."""
    scripts = ["hypridle-manager.py", "hyprland-lid-manager.py"]

    for script in scripts:
        if not Path(script).exists():
            print(f"Error: {script} not found.")
            sys.exit(1)

        # Update shebang if venv used
        if venv_used:
            content = Path(script).read_text()
            new_content = content.replace("#!/usr/bin/env python", f"#!{venv_path}/bin/python")
            Path(script).write_text(new_content)

        # Make executable
        os.chmod(script, 0o755)

        # Install to /usr/local/bin
        dest = Path("/usr/local/bin") / script
        try:
            if os.access("/usr/local/bin", os.W_OK):
                shutil.copy2(script, dest)
            else:
                run_command(["sudo", "cp", script, str(dest)])
        except subprocess.CalledProcessError:
            print(f"Error installing {script}")
            sys.exit(1)

    print("Scripts installed successfully.")

def ensure_lid_config(config_file: Path) -> None:
    """Ensure the config file has the lid_switch section with default values."""
    config = configparser.ConfigParser(interpolation=None)  # Disable interpolation
    config.read(config_file)

    if not config.has_section('lid_switch'):
        config.add_section('lid_switch')
        config.set('lid_switch', 'on_ac_command', 'loginctl lock-session')
        config.set('lid_switch', 'on_battery_command', 'systemctl hibernate')
        config.set('lid_switch', 'low_battery_command', 'systemctl hibernate')

        with open(config_file, 'w') as f:
            config.write(f)
        print("Added lid_switch configuration section to existing config file.")

def ensure_dim_resume_config(config_file: Path) -> None:
    """Ensure the config file has dim_resume_command in all power state sections."""
    config = configparser.ConfigParser(interpolation=None)  # Disable interpolation to handle % characters
    config.read(config_file)

    updated = False
    power_states = ['on_ac', 'on_battery', 'low_battery']

    for state in power_states:
        if config.has_section(state):
            # Check if dim_resume_command is missing
            if not config.has_option(state, 'dim_resume_command'):
                # Add appropriate dim_resume_command based on the dim_command
                try:
                    dim_command = config.get(state, 'dim_command')
                except (configparser.NoOptionError, configparser.NoSectionError):
                    dim_command = ''

                if 'set 10%-' in dim_command:
                    config.set(state, 'dim_resume_command', 'brightnessctl set +10%')
                elif 'set 25%-' in dim_command:
                    config.set(state, 'dim_resume_command', 'brightnessctl set +25%')
                elif 'set 5' in dim_command:
                    config.set(state, 'dim_resume_command', 'brightnessctl set 80%')
                else:
                    # Generic fallback
                    config.set(state, 'dim_resume_command', 'brightnessctl set 100%')
                updated = True

    if updated:
        with open(config_file, 'w') as f:
            config.write(f)
        print("Added dim_resume_command options to existing config file.")

def ensure_notification_config(config_file: Path) -> None:
    """Ensure the config file has notification settings in the general section."""
    config = configparser.ConfigParser(interpolation=None)
    config.read(config_file)

    if not config.has_section('general'):
        config.add_section('general')

    if not config.has_option('general', 'enable_notifications'):
        config.set('general', 'enable_notifications', 'true')

    if not config.has_option('general', 'notification_timeout'):
        config.set('general', 'notification_timeout', '5000')

    with open(config_file, 'w') as f:
        config.write(f)
    print("Ensured notification configuration in config file.")

def setup_config() -> None:
    """Setup configuration directory and copy example config."""
    config_dir = Path.home() / ".config" / "hypridle-handler"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "config.ini"
    if not config_file.exists():
        shutil.copy2("config.ini.example", config_file)
        print(f"Configuration copied to {config_file}")
    else:
        print(f"Configuration already exists at {config_file}")
        # Ensure lid_switch section exists
        ensure_lid_config(config_file)
        # Ensure dim_resume_command options exist
        ensure_dim_resume_config(config_file)
        # Ensure notification settings exist
        ensure_notification_config(config_file)

def find_hyprland_config_files() -> list[Path]:
    """Find all Hyprland config files including those sourced."""
    config_files = []
    hypr_dir = Path.home() / ".config" / "hypr"

    if not hypr_dir.exists():
        return config_files

    # Start with main config file
    main_config = hypr_dir / "hyprland.conf"
    if main_config.exists():
        config_files.append(main_config)

    # Find all config files by parsing source directives
    processed_files = set()

    def process_config_file(config_path: Path) -> None:
        if config_path in processed_files:
            return
        processed_files.add(config_path)

        if not config_path.exists():
            return

        try:
            content = config_path.read_text()
            # Find source directives
            import re
            source_pattern = r'^\s*source\s*=\s*(.+)$'
            matches = re.findall(source_pattern, content, re.MULTILINE)

            for source_path in matches:
                source_path = source_path.strip()
                # Handle relative paths and ~ expansion
                if source_path.startswith('~'):
                    source_path = source_path.replace('~', str(Path.home()))
                elif not source_path.startswith('/'):
                    source_path = str((config_path.parent / source_path).resolve())

                source_file = Path(source_path)
                if source_file.exists() and source_file not in processed_files:
                    config_files.append(source_file)
                    process_config_file(source_file)

        except Exception as e:
            print(f"Warning: Could not process {config_path}: {e}")    # Process all found config files
    for config_file in config_files.copy():
        process_config_file(config_file)

    # Also process the main config file to find its sources
    if main_config.exists():
        process_config_file(main_config)

    return config_files

def update_hyprland_configs(config_files: list[Path]) -> bool:
    """Update all Hyprland config files to comment out conflicting entries."""
    updated_any = False

    for config_file in config_files:
        try:
            content = config_file.read_text()
            original_content = content

            # Comment out hypridle exec-once entries
            import re
            content = re.sub(r'^(\s*exec-once\s*=.*hypridle)', r'# \1', content, flags=re.MULTILINE)
            content = re.sub(r'^(\s*exec-once\s*=.*hypridle-manager)', r'# \1', content, flags=re.MULTILINE)

            # Comment out lid switch bindings that might conflict
            content = re.sub(r'^(\s*bindl\s*=.*switch:(?:on:|off:)?Lid Switch)', r'# \1', content, flags=re.MULTILINE)

            if content != original_content:
                config_file.write_text(content)
                print(f"Updated {config_file} - commented out conflicting entries.")
                updated_any = True

        except Exception as e:
            print(f"Warning: Could not update {config_file}: {e}")

    return updated_any

def setup_systemd(systemd_mode: bool, config_file: Path) -> None:
    """Setup systemd services if requested."""
    if not systemd_mode:
        return

    print("Configuring for systemd mode...")

    # Update config.ini
    config = configparser.ConfigParser(interpolation=None)  # Disable interpolation
    config.read(config_file)
    if not config.has_section('general'):
        config.add_section('general')
    config.set('general', 'systemd_mode', 'true')
    with open(config_file, 'w') as f:
        config.write(f)

    # Find and update all Hyprland config files
    hyprland_configs = find_hyprland_config_files()
    if hyprland_configs:
        print(f"Found {len(hyprland_configs)} Hyprland config file(s)")
        updated = update_hyprland_configs(hyprland_configs)
        if updated:
            print("Updated Hyprland configuration - commented out conflicting exec-once entries.")
        else:
            print("No conflicting exec-once entries found in Hyprland configuration.")
    else:
        print("Warning: No Hyprland config files found.")
        print("Make sure you don't have exec-once entries for hypridle or hypridle-manager.")

    # Create systemd services
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)

    # hypridle.service
    hypridle_service = systemd_dir / "hypridle.service"
    hypridle_service.write_text("""[Unit]
Description=Hyprland Idle Daemon
PartOf=graphical-session.target

[Service]
ExecStart=/usr/bin/hypridle
Restart=always
RestartSec=1

[Install]
WantedBy=graphical-session.target
""")

    # hypridle-manager.service
    manager_service = systemd_dir / "hypridle-manager.service"
    manager_service.write_text("""[Unit]
Description=Hyprland Idle Daemon
PartOf=graphical-session.target

[Service]
ExecStart=/usr/local/bin/hypridle-manager.py
Restart=always
RestartSec=10

[Install]
WantedBy=graphical-session.target
""")

    # Enable and start services
    run_command(["systemctl", "--user", "daemon-reload"])
    run_command(["systemctl", "--user", "enable", "--now", "hypridle-manager.service"])

    print("Systemd services created and started.")

def suggest_lid_binding(config_files: list[Path]) -> None:
    """Suggest adding lid switch binding if not present."""
    has_lid_binding = False

    for config_file in config_files:
        try:
            content = config_file.read_text()
            # Check for various lid switch binding patterns
            if ('bindl' in content and
                ('switch:Lid Switch' in content or
                 'switch:on:Lid Switch' in content or
                 'switch:off:Lid Switch' in content)):
                has_lid_binding = True
                break
        except Exception:
            continue

    if not has_lid_binding:
        print("\nNote: No lid switch binding found in Hyprland configuration.")
        print("To enable lid switch handling, add this to your hyprland.conf:")
        print("  bindl=,switch:Lid Switch,exec,hyprland-lid-manager.py")

def main() -> None:
    """Main installer function."""
    parser = argparse.ArgumentParser(description="Hypridle Manager Installer")
    parser.add_argument("--systemd", action="store_true", help="Enable systemd mode")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")

    args = parser.parse_args()

    check_python()

    venv_path = Path.home() / ".local" / "share" / "hypridle-manager-venv"
    venv_used = install_dependencies(args.skip_deps, venv_path)

    install_scripts(venv_path, venv_used)

    setup_config()

    config_file = Path.home() / ".config" / "hypridle-handler" / "config.ini"
    setup_systemd(args.systemd, config_file)

    print("Installation finished!")
    print("Please edit ~/.config/hypridle-handler/config.ini to your liking.")

    # Suggest lid binding if systemd mode and we found config files
    if args.systemd:
        hyprland_configs = find_hyprland_config_files()
        if hyprland_configs:
            suggest_lid_binding(hyprland_configs)
        else:
            print("For lid switch handling, add to your hyprland.conf:")
            print("  bindl=,switch:Lid Switch,exec,hyprland-lid-manager.py")

if __name__ == "__main__":
    main()
