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


        while True:
            state = driver.execute_script("return window.icalcState")

            if vision and state:
                state['screenshot'] = driver.get_screenshot_as_base64()
            
            try:
                response = requests.post(AGENT_SERVER_URL, json=state, timeout=30)
                response.raise_for_status()
                action = response.json()
            except requests.exceptions.RequestException as e:
                print(f"[Bridge] Connection Error to Agent Server: {e}")
                time.sleep(2)
                continue

            if action:
                print(f"[Bridge] Executing Action: {action['type']}")
                
                if action['type'] == 'click':
                    ActionChains(driver).click().perform()
                    
                elif action['type'] == 'keypress':
                    key_map = {
                        "Enter": Keys.ENTER,
                        "Backspace": Keys.BACK_SPACE,
                        "Escape": Keys.ESCAPE,
                        "m": "m",  # mode toggle
                    }
                    
                    key = action['key']
                    # We map canonical keys (e.g. 'Enter') directly to Selenium Keys.
                    mapped_key = key_map.get(key)
                    if mapped_key:
                        ActionChains(driver).send_keys(mapped_key).perform()
                    elif len(key) == 1 and key not in ['^', '!']:
                        # Standard single char (e.g. '7', '+')
                        ActionChains(driver).send_keys(key).perform()
                    else:
                        # The canonical keys (Escape, Backspace, Enter, m) and single chars 
                        # are handled above.
                        # Complex keys (e.g., 'sin', 'cos'), locate by data-value or data-action and click
                        found = False
                        last_error = None
                        
                        # Reverse map canonical actions for locator fallback (if needed)
                        # The UI uses data-action='all-clear', 'delete', 'calculate'
                        reverse_action_map = {
                            "Escape": "all-clear",
                            "Backspace": "delete",
                            "Enter": "calculate",
                            "m+": "memory-add",
                            "m-": "memory-sub",
                            "mr": "memory-recall",
                            "mc": "memory-clear"
                        }
                        
                        action_name = reverse_action_map.get(key, key)
                        
                        # Combine locators to prevent sequential TimeoutException penalties
                        selector = f'.btn[data-value="{key}"], .btn[data-action="{action_name}"]'
                        
                        try:
                            # Wait for element to be clickable (handles transition/visibility)
                            btn = WebDriverWait(driver, 0.5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                            btn.click()
                            found = True
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
