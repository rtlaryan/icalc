import subprocess
import time
import argparse
import sys
import os
import signal

def run_clients(
    server_ip,
    workers=1,
    worker_offset=0,
    rate=60.0,
    headless=False,
    vision=False,
    quiet=False,
    request_timeout=120.0,
    no_throttle=True,
):
    if not quiet:
        print(f"Starting Client Bridges: Server={server_ip}, Workers={workers}, Offset={worker_offset}, Rate={rate}, Headless={headless}, Vision={vision}")
    
    processes = []
    sink = subprocess.DEVNULL if quiet else None
    
    # Base ports
    base_agent_port = 9000
    base_app_port = 8000
    
    try:
        for i in range(workers):
            agent_port = base_agent_port + worker_offset + i
            app_port = base_app_port + worker_offset + i
            agent_url = f"http://{server_ip}:{agent_port}/step"
            
            if not quiet:
                print(f"Starting Bridge Worker {i+1} (Offset {worker_offset + i}): App Port {app_port} -> Agent {agent_url}")
            
            # Start ICalc Bridge
            bridge_cmd = [sys.executable, "icalc_bridge.py",
                          "--agent-url", agent_url,
                          "--port", str(app_port),
                          "--rate", str(rate),
                          "--request-timeout", str(request_timeout)]
            
            if headless:
                bridge_cmd.append("--headless")

            if vision:
                bridge_cmd.append("--vision")

            if no_throttle:
                bridge_cmd.append("--no-throttle")
                
            bridge_proc = subprocess.Popen(bridge_cmd, stdout=sink, stderr=sink)
            processes.append(bridge_proc)
            
            time.sleep(1)

        if not quiet:
            print("Running bridges... Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            # Check if any bridge died
            active_bridges = [p for p in processes if p.poll() is None]
            if not active_bridges:
                if not quiet:
                    print("All bridges stopped.")
                break
                
    except KeyboardInterrupt:
        if not quiet:
            print("Stopping clients...")
    finally:
        if not quiet:
            print("Terminating all processes...")
        for p in processes:
            if p.poll() is None:
                p.terminate()
                p.wait()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--server-ip', type=str, required=True, help='IP address of the generator server')
    parser.add_argument('--workers', type=int, default=1, help='Number of parallel workers')
    parser.add_argument('--worker-offset', type=int, default=0, help='Offset ID for ports if running multiple clients')
    parser.add_argument('--rate', type=float, default=60.0, help='Transfer rate in Hz')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--vision', action='store_true', help='Enable sending screenshots')
    parser.add_argument('--quiet', action='store_true', help='Suppress bridge output')
    parser.add_argument('--request-timeout', type=float, default=120.0, help='Agent server request timeout in seconds')
    throttle_group = parser.add_mutually_exclusive_group()
    throttle_group.add_argument('--no-throttle', dest='no_throttle', action='store_true', help='Do not sleep between bridge steps')
    throttle_group.add_argument('--throttle', dest='no_throttle', action='store_false', help='Sleep between bridge steps according to --rate')
    parser.set_defaults(no_throttle=True)
    args = parser.parse_args()
    
    run_clients(
        args.server_ip,
        args.workers,
        args.worker_offset,
        args.rate,
        args.headless,
        args.vision,
        args.quiet,
        args.request_timeout,
        args.no_throttle,
    )
