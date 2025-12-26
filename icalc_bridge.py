import http.server
import socketserver
import threading
import os
import time
import json
import sys
import requests
import math

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.action_chains import ActionChains
except ImportError:
    print("Error: Selenium is required. Please install it with: pip install selenium")
    sys.exit(1)

AGENT_SERVER_URL = "http://localhost:9000/step"
ICALC_URL = "http://localhost:8000"

def smooth_move(driver, start_x, start_y, end_x, end_y, duration=0.5):
    steps = 10
    sleep_per_step = duration / steps
    
    actions = ActionChains(driver)
    body = driver.find_element(By.TAG_NAME, "body")
    
    for i in range(1, steps + 1):
        t = i / steps
        current_x = start_x + (end_x - start_x) * t
        current_y = start_y + (end_y - start_y) * t
        
        actions.move_to_element_with_offset(body, 0, 0)
        actions.move_by_offset(int(current_x), int(current_y))
        actions.perform()
        time.sleep(sleep_per_step)

def start_server():
    port = 8000
    # Change to directory of this script to serve correct files
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    handler = http.server.SimpleHTTPRequestHandler
    # Allow address reuse to avoid "Address already in use" errors on quick restarts
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving at port {port}")
        httpd.serve_forever()

def icalc_bridge():
    # Start the server in a background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to start
    time.sleep(1)

    print(f"Starting icalc Bridge Client...")
    print(f"Target App: {ICALC_URL}")
    print(f"Agent Server: {AGENT_SERVER_URL}")

    chrome_options = Options()
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_window_size(1024, 768)
    except Exception as e:
        print(f"Failed to start Chrome Driver: {e}")
        return

    try:
        driver.get(ICALC_URL)
        time.sleep(1)

        current_mouse_x = 0
        current_mouse_y = 0

        while True:
            state = driver.execute_script("return window.icalcState")
            
            try:
                response = requests.post(AGENT_SERVER_URL, json=state)
                response.raise_for_status()
                action = response.json()
            except requests.exceptions.RequestException as e:
                print(f"[Bridge] Connection Error to Agent Server: {e}")
                time.sleep(2)
                continue

            if action:
                print(f"[Bridge] Executing Action: {action['type']}")
                
                if action['type'] == 'move':
                    target_x = action['x']
                    target_y = action['y']
                    smooth_move(driver, current_mouse_x, current_mouse_y, target_x, target_y)
                    current_mouse_x = target_x
                    current_mouse_y = target_y
                    
                elif action['type'] == 'click':
                    ActionChains(driver).click().perform()
                    
                elif action['type'] == 'keypress':
                    key_map = {
                        "Enter": Keys.ENTER,
                        "Backspace": Keys.BACK_SPACE,
                        "Escape": Keys.ESCAPE
                    }
                    key = key_map.get(action['key'], action['key'])
                    ActionChains(driver).send_keys(key).perform()
                
                elif action['type'] == 'terminate':
                    break

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[Bridge] Stopping...")
    except Exception as e:
        print(f"\n[Error] {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    icalc_bridge()
