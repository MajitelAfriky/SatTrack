import machine
import time
from bno055_base import BNO055_BASE

# Configuration
CALIBRATION_FILE = "/data/calibration.txt"
I2C_ADDRESS = 0x29

# I2C and IMU setup
i2c = machine.I2C(0, scl=machine.Pin(9), sda=machine.Pin(8))
imu = BNO055_BASE(i2c, address=I2C_ADDRESS, crystal=False)

def load_calibration():
    try:
        with open(CALIBRATION_FILE, "rb") as f:
            offsets = f.read()
            if len(offsets) == 22:
                # Switch to CONFIG_MODE (0x00)
                i2c.writeto_mem(I2C_ADDRESS, 0x3D, b'\x00')
                time.sleep(0.05)
                
                # Write 22 bytes of calibration data starting at register 0x55
                i2c.writeto_mem(I2C_ADDRESS, 0x55, offsets)
                time.sleep(0.05)
                
                # Switch back to NDOF_MODE (0x0C)
                i2c.writeto_mem(I2C_ADDRESS, 0x3D, b'\x0C')
                time.sleep(0.05)
                return True
    except OSError:
        # File doesn't exist yet, which is fine on first boot
        pass
    return False

def save_calibration():
    try:
        # Switch to CONFIG_MODE (0x00)
        i2c.writeto_mem(I2C_ADDRESS, 0x3D, b'\x00')
        time.sleep(0.05)
        
        # Read 22 bytes of calibration data starting at register 0x55
        offsets = i2c.readfrom_mem(I2C_ADDRESS, 0x55, 22)
        
        # Switch back to NDOF_MODE (0x0C)
        i2c.writeto_mem(I2C_ADDRESS, 0x3D, b'\x0C')
        time.sleep(0.05)
        
        # Save to Pico's flash memory
        with open(CALIBRATION_FILE, "wb") as f:
            f.write(offsets)
        return True
    except Exception:
        return False

def create_bar(value, min_val, max_val, width=40):
    # Constrain value to min/max boundaries
    value = max(min_val, min(max_val, value))
    # Calculate text position
    pos = int((value - min_val) / (max_val - min_val) * width)
    left_space = "-" * pos
    right_space = "-" * (width - pos)
    return f"[{left_space}O{right_space}]"

# --- Main Program Initialization ---
time.sleep(1) # Let the BNO055 boot up

calibration_locked = load_calibration()

# Clear the entire terminal screen once before starting the loop
print('\033[2J', end='')

while True:
    # \033[H moves the cursor to the top-left corner instead of scrolling
    print('\033[H', end='')
    
    # Read calibration status and orientation
    sys_cal, gyro_cal, accel_cal, mag_cal = imu.cal_status()
    heading, roll, pitch = imu.euler()
    
    # Fallback if sensor is busy and returns None
    if heading is None: heading = 0.0
    if roll is None: roll = 0.0
    if pitch is None: pitch = 0.0
    
    # Calibration Lock Logic
    if not calibration_locked:
        if sys_cal == 3 and gyro_cal == 3 and accel_cal == 3 and mag_cal == 3:
            save_calibration()
            calibration_locked = True
            
    # Define UI status text
    status_text = "LOCKED & SAVED" if calibration_locked else "CALIBRATING..."
    
    # Render Dashboard
    print("=========================================")
    print(f" CAL STATUS: SYS({sys_cal}) GYRO({gyro_cal}) ACC({accel_cal}) MAG({mag_cal})")
    print(f" STATE: {status_text}")
    print("=========================================")
    print(f" HEADING (0 to 360) : {heading:>6.1f} deg")
    print(f" {create_bar(heading, 0, 360)}")
    print(f" ROLL (-90 to 90)   : {roll:>6.1f} deg")
    print(f" {create_bar(roll, -90, 90)}")
    print(f" PITCH (-180 to 180): {pitch:>6.1f} deg")
    print(f" {create_bar(pitch, -180, 180)}")
    print("=========================================")
    
    # Refresh rate (~10 FPS)
    time.sleep(0.1)