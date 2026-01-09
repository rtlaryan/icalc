import http.server
import argparse
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
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
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

def start_server(port):
    # Change to directory of this script to serve correct files
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    handler = http.server.SimpleHTTPRequestHandler
    # Allow address reuse to avoid "Address already in use" errors on quick restarts
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving at port {port}")
        httpd.serve_forever()

def icalc_bridge(vision=False, rate=60.0, agent_url=None, app_port=8000, headless=False):
    global AGENT_SERVER_URL, ICALC_URL
    if agent_url:
        AGENT_SERVER_URL = agent_url
    
    ICALC_URL = f"http://localhost:{app_port}"
    
    # Start the server in a background thread
    server_thread = threading.Thread(target=start_server, args=(app_port,), daemon=True)
    server_thread.start()
    
    # Give the server a moment to start
    time.sleep(1)

    print(f"Starting icalc Bridge Client...")
    print(f"Target App: {ICALC_URL}")
    print(f"Agent Server: {AGENT_SERVER_URL}")

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_window_size(1024, 768)
    except Exception as e:
        print(f"Failed to start Chrome Driver: {e}")
        return

    try:
        driver.get(ICALC_URL)
        time.sleep(1)

        if vision:
            driver.execute_script("""
                const cursor = document.createElement('div');
                cursor.style.position = 'fixed';
                cursor.style.width = '20px';
                cursor.style.height = '20px';
                cursor.style.borderRadius = '50%';
                cursor.style.backgroundColor = 'rgba(255, 0, 0, 0.5)';
                cursor.style.pointerEvents = 'none';
                cursor.style.zIndex = '9999';
                cursor.style.transform = 'translate(-50%, -50%)';
                cursor.id = 'agent-cursor';
                document.body.appendChild(cursor);

                document.addEventListener('mousemove', (e) => {
                    cursor.style.left = e.clientX + 'px';
                    cursor.style.top = e.clientY + 'px';
                });
            """)

        current_mouse_x = 0
        current_mouse_y = 0

        while True:
            state = driver.execute_script("return window.icalcState")

            if vision and state:
                state['screenshot'] = driver.get_screenshot_as_base64()
            
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
                    
                    key = action['key']
                    if key in key_map or len(key) == 1:
                        # Standard key or mapped special key
                        mapped_key = key_map.get(key, key)
                        ActionChains(driver).send_keys(mapped_key).perform()
                    else:
                        # Complex key (e.g., 'sin', 'cos'), locate by data-value or data-action and click
                        found = False
                        last_error = None
                        
                        # Define locators
                        locators = [
                            (By.CSS_SELECTOR, f'.btn[data-value="{key}"]'),
                            (By.CSS_SELECTOR, f'.btn[data-action="{key}"]')
                        ]
                        
                        for by, selector in locators:
                            try:
                                # Wait for element to be clickable (handles transition/visibility)
                                btn = WebDriverWait(driver, 0.5).until(EC.element_to_be_clickable((by, selector)))
                                btn.click()
                                found = True
                                break
                            except Exception as e:
                                last_error = e
                        
                        if not found:
                             print(f"[Bridge] Warning: Could not find/click button for key '{key}': {last_error}")
                
                elif action['type'] == 'terminate':
                    break

            time.sleep(1.0 / rate)

    except KeyboardInterrupt:
        print("\n[Bridge] Stopping...")
    except Exception as e:
        print(f"\n[Error] {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Bridge for icalc')
    parser.add_argument('--vision', action='store_true', help='Enable sending screenshots')
    parser.add_argument('--rate', type=float, default=60.0, help='Transfer rate in Hz')
    parser.add_argument('--agent-url', type=str, help='Full URL of the agent step endpoint')
    parser.add_argument('--port', type=int, default=8000, help='Port to serve the app on')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    args = parser.parse_args()

    icalc_bridge(vision=args.vision, rate=args.rate, agent_url=args.agent_url, app_port=args.port, headless=args.headless)
