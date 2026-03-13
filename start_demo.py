import time
import sys
import threading
import logging
import os
from datetime import datetime, timedelta

# Safely mute Flask request logs without breaking the server
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Import your custom modules
from sensor_reader import SerialReader
from pi_sensors import PiSensorManager
from telegram_alerts import TelegramManager
from sensor_health_check import HealthMonitor
from flask_server import start_web_server

def get_sparkline(history):
    chars = " ▂▃▄▅▆▇█"
    line = ""
    for val in history:
        idx = int(max(0, min(100, val)) / 12.5)
        line += chars[idx]
    return line

def main():
    G = "\033[1;32m"; Y = "\033[1;33m"; R = "\033[1;31m"; B = "\033[1;34m"
    C = "\033[1;36m"; W = "\033[1;37m"; RST = "\033[0m"; BLD = "\033[1m"
    P = "\033[1;35m" # Purple for Piezo

    os.system('clear')
    print(f"{C}🚀 Initializing JARVIS Elite Phase 1...{RST}")

    # --- REALISTIC SENSOR PROFILES ---
    print(f"\n{Y}{BLD}--- SELECT CARGO PROFILE ---{RST}")
    print("1: CUCUMBER (Fungus/Rot Sensitive)")
    print("2: APPLE/FRUIT (Ethylene/Alcohol Sensitive)")
    print("3: ONION/POTATO (Sulfur/Methane Sensitive)")
    print("4: BANANA (Ethylene/Ester Sensitive)")
    print("5: DEFAULT")
    choice = input(f"{W}Select Cargo Type [1]: {RST}") or "1"

    # Format: Name, MQ135_Fresh, MQ135_Rot, MQ3_Fresh, MQ3_Rot
    profiles = {
            "1": ("CUCUMBER", 175, 215, 370, 405),
            "2": ("FRUIT", 200, 350, 350, 600),
            "3": ("TUBER", 220, 400, 300, 450),
            "4": ("BANANA", 125, 200, 150, 350), 
            "5": ("DEFAULT", 180, 300, 300, 500)
    }
    active_prof = profiles.get(choice, profiles["1"])
    print(f"{G}Profile loaded: {active_prof[0]}{RST}\n")

    tg_mgr = TelegramManager()
    health_mon = HealthMonitor(tg_mgr)

    # Make sure this matches your blue cable port! (/dev/ttyACM0 or /dev/ttyUSB0)
    reader = SerialReader(port='/dev/ttyACM0', baud=9600)
    if not reader.start():
        print(f"{R}❌ CRITICAL: Arduino disconnected. Check USB/Serial.{RST}")
        sys.exit(1)

    print(f"{C}🌐 Booting Web Server on Port 8080...{RST}")
    PiSensorManager(reader).start()
    threading.Thread(target=start_web_server, args=(reader,), daemon=True).start()

    time.sleep(3)
    risk_history = [0] * 35

    # --- VIBRATION FILTER VARIABLES ---
    baseline_vib = None
    rumble_lockout_time = 0 
    pest_alert = False

    try:
        while True:
            with reader.lock:
                data = reader.latest_data.copy()

            # --- SENSOR FETCHING ---
            mq135 = data.get('m135', active_prof[1])
            mq3   = data.get('m3', active_prof[3])
            # Assuming your sensor_reader parses the first Arduino value as 'vib'
            current_vib = data.get('vib', 0) 

            # --- THE "EARTHQUAKE vs PEST" FILTER ---
            vib_status = f"{G}STABLE{RST}"
            pest_alert = False
            
            if baseline_vib is None and current_vib > 0:
                baseline_vib = current_vib # Set initial zero-point

            if baseline_vib is not None:
                vib_diff = abs(current_vib - baseline_vib)
                current_time = time.time()

                # 1. EARTHQUAKE / CARRYING DETECTED (Massive spike)
                if vib_diff > 100: 
                    rumble_lockout_time = current_time + 5.0 # Lockout for 5 seconds
                    vib_status = f"{Y}🚚 TRANSIT RUMBLE{RST}"
                
                # 2. PEST / MICRO-TAP DETECTED (Small spike, and NOT currently locked out)
                elif vib_diff > 10 and current_time > rumble_lockout_time:
                    pest_alert = True
                    vib_status = f"{R}🐛 PEST ACTIVITY!{RST}"
                
                # 3. COOL DOWN (We are locked out because of recent carrying)
                elif current_time <= rumble_lockout_time:
                    vib_status = f"{Y}🚚 TRANSIT RUMBLE{RST}"

                # Slowly adjust baseline to account for temperature drift in the op-amp
                baseline_vib = (baseline_vib * 0.95) + (current_vib * 0.05)


            # --- JARVIS SMART SPOILAGE MATH ---
            risk_135 = ((mq135 - active_prof[1]) / (active_prof[2] - active_prof[1])) * 100
            risk_3 = ((mq3 - active_prof[3]) / (active_prof[4] - active_prof[3])) * 100
            smart_risk = max(5.0, min(99.9, (risk_135 + risk_3) / 2))
            risk = smart_risk

            health_factor = (100 - risk) / 100.0
            hours_left = max(1, int(168 * (health_factor ** 3)))
            decay_str = (datetime.now() + timedelta(hours=hours_left)).strftime("%a %d %b, %H:%M")

            with reader.lock:
                reader.latest_data['risk'] = risk
                reader.latest_data['decay_str'] = decay_str

            risk_history.append(risk)
            risk_history.pop(0)

            dist = data.get('dist', 0.0)
            dist_str = f"{R}FAULT{RST}" if dist <= 0.0 else f"{W}{dist:.1f} cm{RST}"
            clr = G if risk < 20 else (Y if risk < 50 else R)

            # --- ELITE UI RENDERING ---
            print("\033[H\033[J", end="")
            print(f"{BLD}{C}╔══════════════════════════════════════════════════════════════════════╗{RST}")
            print(f"{BLD}{C}║   JARVIS ELITE | {active_prof[0]:<10} | PIEZO+GAS ACTIVE                 ║{RST}")
            print(f"{BLD}{C}╚══════════════════════════════════════════════════════════════════════╝{RST}")

            print(f"  {BLD}ACOUSTIC & VIBRATION SENSE:{RST}")
            print(f"  Piezo Discs: {P}{int(current_vib):>4}{RST}  |  State: {vib_status}")
            print("-" * 72)

            print(f"  {BLD}RAW GAS SENSORS (10-BIT ADC):{RST}")
            print(f"  MQ-135 (Air): {W}{int(mq135):>4}{RST}  |  MQ-3 (Alc): {W}{int(mq3):>4}{RST}")
            print(f"  MQ-4 (Meth):  {W}{int(data.get('m4',0)):>4}{RST}  |  MQ-2 (Smk): {W}{int(data.get('m2',0)):>4}{RST}")
            print("-" * 72)

            print(f"  {BLD}LOGISTICS CLIMATE:{RST}")
            print(f"  TEMP: {Y}{data.get('t',0):.1f}°C{RST}   HUM: {B}{data.get('h',0):.1f}%{RST}   CARGO: {dist_str}")
            print("-" * 72)

            print(f"  {BLD}ASCII RISK GRAPH:{RST} [{clr}{get_sparkline(risk_history)}{RST}]")
            print(f"  {BLD}SPOILAGE RISK   :{RST} {clr}{risk:>5.1f}%{RST}")
            print(f"  {BLD}EST. DECAY TIME :{RST} {BLD}{Y}{decay_str}{RST}")
            print("-" * 72)

            mot = data.get('mot', 0)
            sec = f"{R}!! INTRUSION !!{RST}" if mot == 1 else f"{G}SECURE{RST}"
            print(f"  {BLD}SECURITY:{RST} {sec}   |   {BLD}WEB UI:{RST} http://192.168.0.5:8080")
            print(f"{BLD}{C}╚══════════════════════════════════════════════════════════════════════╝{RST}")

            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{G}✅ Safe Shutdown. Go to sleep!{RST}")
        sys.exit(0)

if __name__ == "__main__":
    main()
