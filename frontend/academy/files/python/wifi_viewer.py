# wifi_viewer.py - see the WiFi passwords saved on YOUR OWN Windows PC
# Run it on your own computer. It only shows networks this PC has already joined.
import subprocess


def get_wifi_profiles():
    """Return the names of every WiFi network saved on this PC."""
    out = subprocess.check_output(
        ["netsh", "wlan", "show", "profiles"], text=True
    )
    names = []
    for line in out.splitlines():
        if "All User Profile" in line:
            names.append(line.split(":", 1)[1].strip())
    return names


def get_wifi_password(name):
    """Return the saved password for one network, or a note if there is none."""
    try:
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "profile", name, "key=clear"], text=True
        )
    except subprocess.CalledProcessError:
        return "N/A"
    for line in out.splitlines():
        if "Key Content" in line:
            return line.split(":", 1)[1].strip()
    return "(open network - no password)"


def main():
    names = get_wifi_profiles()
    if not names:
        print("No saved WiFi networks found on this PC.")
        return
    for name in names:
        print(name, "->", get_wifi_password(name))


if __name__ == "__main__":
    main()
