
import subprocess
import time
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class MockAgent(BaseHTTPRequestHandler):
    step_count = 0
    
    def log_message(self, format, *args):
        pass # Silence logs

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        state = json.loads(post_data)
        
        response_action = None
        
        # Step 0: Initial state. Action: Toggle mode (click mode-toggle or key m)
        # Step 1: Wait a bit? Or immediately try tan?
        # We need to test if the "wait" time is enough.
        # If we send 'm' then 'tan' in next step:
        # Bridge receives 'm', clicks. Loop continues. Sleep 1/rate.
        # Bridge receives 'tan', tries to click.
        
        if MockAgent.step_count == 0:
            print("[MockAgent] Step 0: Toggling Mode")
            response_action = {"type": "keypress", "key": "m"}
        elif MockAgent.step_count == 1:
            print("[MockAgent] Step 1: Clicking tan")
            response_action = {"type": "keypress", "key": "tan"}
        else:
             response_action = {"type": "terminate"}

        MockAgent.step_count += 1
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_action).encode())

def run_reproduction():
    server_address = ('', 9011)
    httpd = HTTPServer(server_address, MockAgent)
    httpd.timeout = 1.0 # 1 second timeout for handle_request
    
    print("Mock Agent running on 9011...")
    
    # Start Bridge
    print("Starting Bridge...")
    cmd = [sys.executable, "-u", "icalc_bridge.py", "--agent-url", "http://localhost:9011", "--port", "8082", "--headless", "--rate", "10"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    start_time = time.time()
    steps_handled = 0
    
    try:
        while steps_handled < 3:
            if proc.poll() is not None:
                print("Bridge process died unexpectedly!")
                break
                
            if time.time() - start_time > 15: # Timeout
                print("Test Timed Out!")
                break
                
            try:
                # Handle one request
                httpd.handle_request() 
                # If handle_request returns, it processed a request OR timed out?
                # creating a custom request handler to track? 
                # Actually handle_request does not raise timeout, it just returns?
                # No, socket timeout?
                # Let's trust that handle_request blocks for at most 1s if timeout set
                steps_handled = MockAgent.step_count # usage of class var is flaky if multiple instances, but here ok
                # Wait, step_count is instance var? No `step_count = 0` at class level.
            except Exception as e:
                print(f"Server error: {e}")
                
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except:
                proc.kill()
                stdout, stderr = proc.communicate()
        else:
            stdout, stderr = proc.communicate()
            
        print("Bridge Output:\n", stdout)
        print("Bridge Errors:\n", stderr)

        # Check for success verification
        # We EXPECT failure to find 'tan' button in stderr/stdout
        if "Could not find/click button for key 'tan'" in stdout:
            print("SUCCESS: Reproduced failure (Task succeeded).")
        else:
            if "tan" in stdout and "Searching" in stdout: # Generic check?
                pass
            print("FAILURE: Did not reproduce failure (Or bridge crashed differently).")

if __name__ == "__main__":
    run_reproduction()
