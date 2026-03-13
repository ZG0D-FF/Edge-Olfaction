import serial
import time

# UART GPIO pins
arduino_port = '/dev/serial0' 

try:
    # Adding a short timeout so it doesn't hang forever
    ser = serial.Serial(arduino_port, 9600, timeout=0.1)
    time.sleep(2) 
    ser.reset_input_buffer() # Nuke the old data backlog
    print(f"[OK] UART Link Active on {arduino_port}")
except Exception as e:
    print(f"[FAIL] UART Error: {e}")
    exit()

print("--- JARVIS EDGE OLFACTION: FAST TAP MODE ---")
baseline_piezo = None

while True:
    # Check if there is ANY data at all
    if ser.in_waiting > 0:
        try:
            raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
            
            if not raw_line:
                continue

            # Split the data (Piezo,MQ2,MQ3,MQ4,MQ135,Temp,Hum)
            data = raw_line.split(',')
            
            # Use whatever data comes, even if a few MQs are missing
            if len(data) >= 1:
                try:
                    piezo_val = int(data[0])
                    
                    if baseline_piezo is None:
                        baseline_piezo = piezo_val
                        print(f"[READY] Baseline: {baseline_piezo}. TAP NOW!")
                        continue
                    
                    # Detection Logic
                    diff = abs(piezo_val - baseline_piezo)
                    
                    if diff > 15: # Sensitivity threshold
                        bar = "█" * min(int(diff / 2), 50)
                        print(f"💥 TAP! Value: {piezo_val} | Diff: {diff} | {bar}")
                    else:
                        # Print live values in one line to show it's alive
                        print(f"Listening... Raw: {piezo_val}      ", end='\r')
                except ValueError:
                    pass # Skip if data is scrambled
                        
        except Exception as e:
            print(f"\n[ERROR]: {e}")
            
    time.sleep(0.01) # Ultra-fast scanning
