import subprocess
import time
import argparse
import sys
import os
import signal

def run_clients(server_ip, workers=1, rate=60.0, headless=False):
    print(f"Starting Client Bridges: Server={server_ip}, Workers={workers}, Rate={rate}, Headless={headless}")
    
    processes = []
    
    # Base ports
    base_agent_port = 9000
    base_app_port = 8000
    
    try:
        for i in range(workers):
            agent_port = base_agent_port + i
            app_port = base_app_port + i
            agent_url = f"http://{server_ip}:{agent_port}/step"
            
            print(f"Starting Bridge Worker {i+1}: App Port {app_port} -> Agent {agent_url}")
            
            # Start ICalc Bridge
            bridge_cmd = [sys.executable, "icalc_bridge.py",
                          "--agent-url", agent_url,
                          "--port", str(app_port),
                          "--rate", str(rate)]
            
            if headless:
                bridge_cmd.append("--headless")
                
            bridge_proc = subprocess.Popen(bridge_cmd, stdout=sys.stdout, stderr=sys.stderr)
            processes.append(bridge_proc)
            
            time.sleep(1)

        print("Running bridges... Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            # Check if any bridge died
            active_bridges = [p for p in processes if p.poll() is None]
            if not active_bridges:
                print("All bridges stopped.")
                break
                
    except KeyboardInterrupt:
        print("Stopping clients...")
    finally:
        print("Terminating all processes...")
        for p in processes:
            if p.poll() is None:
                p.terminate()
                p.wait()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--server-ip', type=str, required=True, help='IP address of the generator server')
    parser.add_argument('--workers', type=int, default=1, help='Number of parallel workers')
    parser.add_argument('--rate', type=float, default=60.0, help='Transfer rate in Hz')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    args = parser.parse_args()
    
    run_clients(args.server_ip, args.workers, args.rate, args.headless)
