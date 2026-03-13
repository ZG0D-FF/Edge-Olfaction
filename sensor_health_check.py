import threading
import time

class HealthMonitor:
    def __init__(self, tg_mgr):
        self.tg_mgr = tg_mgr
        self.running = False
        self.reader = None

    def start_monitoring(self, reader):
        self.reader = reader
        self.running = True
        threading.Thread(target=self._health_loop, daemon=True).start()
        print("✅ Telegram Health Watchdog Active")

    def _health_loop(self):
        while self.running:
            if self.reader:
                with self.reader.lock:
                    data = self.reader.latest_data
                
                # Check for critical hardware failure (e.g. Arduino sends 0.0 for Temp)
                if data.get('t', 1.0) == 0.0 and data.get('h', 1.0) == 0.0:
                    msg = "🚨 JARVIS CRITICAL: DHT11 Environment Sensor Offline!"
                    self.tg_mgr.send_alert(msg, category="health")
                    
            time.sleep(60) # Only run the health check once a minute
