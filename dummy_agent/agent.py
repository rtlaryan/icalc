import http.server
import socketserver
import json
import sys
import os
import threading

PORT = 9000


latest_state = {}
state_lock = threading.Lock()

class AgentHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            try:
                with open('dashboard.html', 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'Dashboard not found')
        
        elif self.path == '/state':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            with state_lock:
                # current state might include big base64 string
                self.wfile.write(json.dumps(latest_state).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global latest_state
        if self.path == '/step':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                state = json.loads(post_data.decode('utf-8'))
                
                with state_lock:
                    latest_state = state

                # print("\n--- Intercepted State ---")
                # print(json.dumps(state)) # Commented out to reduce noise
                # sys.stdout.flush() 
            except json.JSONDecodeError:
                print("Failed to decode JSON state")

            # Send a response. 
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {} # No action
            self.wfile.write(json.dumps(response).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Override to suppress default logging to stderr which might clutter output
        return

def run_server():
    # Change to directory of this script to serve dashboard.html correctly
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Allow reuse of address to avoid "Address already in use" errors during quick restarts
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), AgentHandler) as httpd:
        print(f"Dummy Agent Server running on port {PORT}")
        print(f"Dashboard available at http://localhost:{PORT}")
        print("Waiting for state data from icalc_bridge...")
        sys.stdout.flush()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()
