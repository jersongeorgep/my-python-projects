import platform
import subprocess
import ctypes
import time
import os
from datetime import datetime

def get_idle_duration():
    """Get system idle time in seconds for Windows, Linux, and macOS"""
    system = platform.system()

    if system == "Windows":
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return millis / 1000.0  # Convert to seconds
        return 0

    elif system == "Linux":
        try:
            output = subprocess.check_output(["xprintidle"])
            return int(output) / 1000.0
        except FileNotFoundError:
            raise Exception("xprintidle not found. Install with: sudo apt install xprintidle")
        except subprocess.CalledProcessError:
            return 0  # Fallback if xprintidle fails

    elif system == "Darwin":  # macOS
        try:
            output = subprocess.check_output(
                ['ioreg', '-c', 'IOHIDSystem'],
                universal_newlines=True
            )
            for line in output.split('\n'):
                if 'HIDIdleTime' in line:
                    nanoseconds = int(line.split('=')[-1].strip())
                    return nanoseconds / 1e9
            return 0
        except subprocess.CalledProcessError:
            return 0  # Fallback if ioreg fails

    else:
        raise NotImplementedError(f"Unsupported OS: {system}")

def show_notification(message):
    """Show system notification appropriate for the OS"""
    system = platform.system()

    if system == "Linux":
        os.system(f'notify-send "Idle Alert" "{message}"')
    elif system == "Windows":
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast("Idle Alert", message, duration=5)
        except ImportError:
            print("Install win10toast: pip install win10toast")
    elif system == "Darwin":  # macOS
        os.system(f'''osascript -e 'display notification "{message}" with title "Idle Alert"' ''')

def log_idle_time(idle_time, log_file="idle_time_log.txt"):
    """Log idle time to a file"""
    with open(log_file, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - Idle time: {idle_time:.2f} seconds\n")

def main():
    """Main tracking loop"""
    IDLE_LIMIT = 300  # 5 minutes in seconds
    CHECK_INTERVAL = 10  # Check every 10 seconds
    
    print("Starting idle time tracker. Press Ctrl+C to stop...")
    try:
        while True:
            idle_time = get_idle_duration()
            print(f"Current idle time: {idle_time:.2f} seconds")
            log_idle_time(idle_time)
            
            if idle_time > IDLE_LIMIT:
                alert_msg = f"You've been idle for {int(idle_time//60)} minutes!"
                show_notification(alert_msg)
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nIdle time tracking stopped.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()