#!/usr/bin/env python3
"""
AdShare Monitor v6.0 - Combined Solution
Browser setup + userscript installation + monitoring
"""

import subprocess
import time
import re
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import signal
import sys
import json
from pathlib import Path
import urllib.request
import cv2
from io import BytesIO

try:
    import requests
    from bs4 import BeautifulSoup
    import pytz
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from PIL import Image
except ImportError:
    print("Installing required packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", 
                   "selenium", "requests", "beautifulsoup4", "pytz", 
                   "opencv-python-headless", "Pillow"], check=True)
    import requests
    from bs4 import BeautifulSoup
    import pytz
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from PIL import Image

# ==================== CONFIGURATION ====================

CONFIG = {
    'telegram_token': "8332516699:AAF8287h5Be4ejvhoFpcYiHG4YHVJlH_R0g",
    'chat_id': None,
    
    # Login credentials
    'email': 'jiocloud90@gmail.com',
    'password': '@Sd2007123',
    
    # Competition Settings
    'leaderboard_check_interval': 600,  # 10 minutes
    'safety_margin': 250,
    'competition_strategy': 'today_only',
    'my_user_id': '4242',
    
    # Browser Settings
    'browser_url': "https://adsha.re/surf",
    'browser_width': '1280',
    'browser_height': '720',
    'headless_mode': True,  # True for Railway
    
    # Technical Settings
    'leaderboard_url': 'https://adsha.re/ten',
    'cookies': '',
    'timezone': 'Asia/Kolkata',
    
    # Profile paths
    'profile_dir': '/app/firefox_profile',
    'extensions_dir': '/app/extensions',
    'screenshots_dir': '/app/screenshots',
    
    # Auto Start
    'auto_start': True,
}

# Extensions configuration
EXTENSIONS = {
    "violentmonkey": {
        "xpi_url": "https://addons.mozilla.org/firefox/downloads/file/4455138/violentmonkey-2.31.0.xpi",
        "xpi_file": "violentmonkey.xpi",
        "name": "Violentmonkey"
    },
    "ublock": {
        "xpi_url": "https://addons.mozilla.org/firefox/downloads/file/4598854/ublock_origin-1.67.0.xpi",
        "xpi_file": "ublock_origin.xpi",
        "name": "uBlock Origin"
    }
}

USERSCRIPT_JS = "https://update.greasyfork.org/scripts/551435/Very%20Smart%20Symbol%20Game%20Auto-Solver%20Pro%20v34.user.js"
USERSCRIPT_PAGE = "https://greasyfork.org/en/scripts/551435-very-smart-symbol-game-auto-solver-pro-v3-4"

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('adshare_monitor.log')
    ]
)
logger = logging.getLogger(__name__)

# ==================== STATE MANAGEMENT ====================

class MonitorState:
    def __init__(self):
        self.is_running = False
        self.browser_active = False
        self.driver = None
        self.leaderboard = []
        self.my_position = None
        self.target_achieved = False
        self.current_target = 0
        self.strategy = CONFIG['competition_strategy']
        self.safety_margin = CONFIG['safety_margin']
        self.last_my_credits = 0
        self.last_credits_time = None
        self.credits_growth_rate = 0
        self.last_check_time = None
        self.is_logged_in = False
        self.extensions_installed = False

state = MonitorState()

# ==================== BROWSER SETUP & USERSCRIPT INSTALLATION ====================

def download_files():
    """Download extensions"""
    os.makedirs(CONFIG['extensions_dir'], exist_ok=True)
    logger.info("Downloading extensions...")
    
    paths = {}
    for ext_id, ext_info in EXTENSIONS.items():
        filepath = os.path.join(CONFIG['extensions_dir'], ext_info["xpi_file"])
        if not os.path.exists(filepath):
            urllib.request.urlretrieve(ext_info["xpi_url"], filepath)
            logger.info(f"Downloaded {ext_info['name']}")
        paths[ext_id] = filepath
    
    return paths

def take_screenshot(driver, name, description=""):
    """Take screenshot and return image data for Telegram"""
    try:
        os.makedirs(CONFIG['screenshots_dir'], exist_ok=True)
        path = f"{CONFIG['screenshots_dir']}/{name}.png"
        driver.save_screenshot(path)
        
        # Convert to bytes for Telegram
        with open(path, 'rb') as f:
            image_data = f.read()
        
        logger.info(f"Screenshot: {description or name}")
        return image_data
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return None

def install_userscript_properly(driver):
    """Install userscript with proper window handling"""
    logger.info("Starting userscript installation...")
    
    try:
        # Get initial window handle
        main_window = driver.current_window_handle
        initial_windows = driver.window_handles
        
        # Go to Greasyfork page
        logger.info("Opening Greasyfork page...")
        driver.get(USERSCRIPT_PAGE)
        time.sleep(6)
        
        # Check if install link exists
        page_source = driver.page_source
        if "install this script" not in page_source.lower():
            logger.error("Violentmonkey not detected by Greasyfork!")
            return False
        
        logger.info("Violentmonkey detected!")
        
        # Click install link
        logger.info("Clicking install link...")
        try:
            install_link = driver.find_element(By.CSS_SELECTOR, "a.install-link")
            install_link.click()
            logger.info("Clicked install link")
        except Exception as e:
            logger.warning(f"Direct click failed, trying JS: {e}")
            driver.execute_script("document.querySelector('a.install-link').click();")
            logger.info("JS click executed")
        
        # Wait for new window to open
        time.sleep(5)
        
        # Check for new windows
        current_windows = driver.window_handles
        
        if len(current_windows) > len(initial_windows):
            logger.info("New window detected!")
            
            # Switch to the newest window
            new_window = [w for w in current_windows if w not in initial_windows][-1]
            driver.switch_to.window(new_window)
            
            time.sleep(3)
            
            # Look for Install button
            logger.info("Looking for Install button...")
            
            install_selectors = [
                (By.XPATH, "//button[contains(text(), 'Install')]"),
                (By.XPATH, "//button[contains(@class, 'install')]"),
                (By.CSS_SELECTOR, "button.vm-confirm"),
                (By.XPATH, "//button[@type='submit']"),
            ]
            
            installed = False
            for by, selector in install_selectors:
                try:
                    install_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    install_btn.click()
                    logger.info(f"Clicked Install button using {selector}")
                    installed = True
                    time.sleep(3)
                    break
                except:
                    continue
            
            if not installed:
                logger.warning("No Install button found, trying keyboard shortcut...")
                actions = webdriver.ActionChains(driver)
                actions.key_down(Keys.CONTROL).send_keys(Keys.RETURN).key_up(Keys.CONTROL).perform()
                logger.info("Sent Ctrl+Enter")
                time.sleep(3)
            
            # Close install window and switch back
            driver.close()
            driver.switch_to.window(main_window)
            
            logger.info("Userscript installation completed!")
            return True
        else:
            logger.error("No new window opened!")
            return False
            
    except Exception as e:
        logger.error(f"Error during installation: {e}")
        return False

def setup_browser():
    """Setup Firefox browser with extensions and userscript"""
    logger.info("Setting up browser...")
    
    # Clean profile directory
    if os.path.exists(CONFIG['profile_dir']):
        import shutil
        shutil.rmtree(CONFIG['profile_dir'])
    os.makedirs(CONFIG['profile_dir'])
    
    # Download extensions
    extension_paths = download_files()
    
    # Firefox options
    options = Options()
    if CONFIG['headless_mode']:
        options.add_argument("--headless")
    options.add_argument(f"--width={CONFIG['browser_width']}")
    options.add_argument(f"--height={CONFIG['browser_height']}")
    options.set_preference("xpinstall.signatures.required", False)
    options.set_preference("extensions.autoDisableScopes", 0)
    options.set_preference("extensions.enabledScopes", 15)
    
    # Create driver
    driver = webdriver.Firefox(options=options)
    
    try:
        # Install extensions
        for ext_id, ext_path in extension_paths.items():
            abs_path = os.path.abspath(ext_path)
            driver.install_addon(abs_path, temporary=False)
            logger.info(f"Installed {EXTENSIONS[ext_id]['name']}")
            time.sleep(3)
        
        # Restart browser to load extensions properly
        driver.quit()
        time.sleep(3)
        
        # Create new driver instance
        driver = webdriver.Firefox(options=options)
        logger.info("Browser restarted with extensions")
        
        # Wait for extensions to load
        time.sleep(10)
        
        # Install userscript
        success = install_userscript_properly(driver)
        if success:
            state.extensions_installed = True
            logger.info("All extensions and userscript installed successfully!")
        else:
            logger.warning("Userscript installation failed, but continuing...")
        
        return driver
        
    except Exception as e:
        logger.error(f"Browser setup error: {e}")
        if driver:
            driver.quit()
        return None

def force_login(driver):
    """Login to AdShare"""
    try:
        logger.info("Attempting login...")
        
        login_url = "https://adsha.re/login"
        driver.get(login_url)
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(3)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        form = soup.find('form', {'name': 'login'})
        if not form:
            logger.error("No login form found")
            return False
        
        password_field_name = None
        for field in form.find_all('input'):
            field_name = field.get('name', '')
            field_value = field.get('value', '')
            
            if field_value == 'Password' and field_name != 'mail' and field_name:
                password_field_name = field_name
                break
        
        if not password_field_name:
            logger.error("No password field found")
            return False
        
        logger.info(f"Password field: {password_field_name}")
        
        # Fill email
        email_selectors = [
            "input[name='mail']",
            "input[type='email']",
            "input[placeholder*='email' i]",
        ]
        
        email_filled = False
        for selector in email_selectors:
            try:
                email_field = driver.find_element(By.CSS_SELECTOR, selector)
                email_field.clear()
                email_field.send_keys(CONFIG['email'])
                logger.info("Email entered successfully")
                email_filled = True
                break
            except:
                continue
        
        if not email_filled:
            logger.error("Could not fill email field")
            return False
        
        time.sleep(2)
        
        # Fill password
        password_selectors = [
            f"input[name='{password_field_name}']",
            "input[type='password']",
            "input[placeholder*='password' i]",
        ]
        
        password_filled = False
        for selector in password_selectors:
            try:
                password_field = driver.find_element(By.CSS_SELECTOR, selector)
                password_field.clear()
                password_field.send_keys(CONFIG['password'])
                logger.info("Password entered successfully")
                password_filled = True
                break
            except:
                continue
        
        if not password_filled:
            return False
        
        time.sleep(2)
        
        # Click login
        login_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button",
            "input[value*='Login']",
        ]
        
        login_clicked = False
        for selector in login_selectors:
            try:
                login_btn = driver.find_element(By.CSS_SELECTOR, selector)
                if login_btn.is_displayed() and login_btn.is_enabled():
                    login_btn.click()
                    logger.info("Login button clicked successfully")
                    login_clicked = True
                    break
            except:
                continue
        
        if not login_clicked:
            try:
                form_element = driver.find_element(By.CSS_SELECTOR, "form[name='login']")
                form_element.submit()
                logger.info("Form submitted successfully")
                login_clicked = True
            except:
                pass
        
        time.sleep(8)
        
        # Navigate to surf page
        driver.get("https://adsha.re/surf")
        time.sleep(5)
        
        # Check if login successful
        current_url = driver.current_url
        if "surf" in current_url or "game" in current_url.lower():
            logger.info("Login successful!")
            state.is_logged_in = True
            send_telegram_message("✅ Login Successful!")
            return True
        else:
            logger.error("Login failed")
            return False
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return False

# ==================== MONITORING FUNCTIONS ====================

class LeaderboardParser:
    @staticmethod
    def parse_with_beautifulsoup(html: str) -> List[Dict]:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            leaderboard = []
            
            selectors = [
                'div[style*="width:250px"][style*="margin:5px auto"]',
                'div[style*="width:250px"]',
                'div[style*="margin:5px auto"]',
            ]
            
            entries = []
            for selector in selectors:
                entries = soup.select(selector)
                if entries:
                    break
            
            if not entries:
                all_divs = soup.find_all('div')
                entries = [div for div in all_divs if 'T:' in div.get_text() and 'Y:' in div.get_text()]
            
            rank = 1
            for entry in entries:
                text = entry.get_text(strip=True)
                
                user_match = re.search(r'#(\d+)', text)
                if not user_match:
                    continue
                
                user_id = user_match.group(1)
                
                today_match = re.search(r'T:\s*(\d+(?:,\d+)*)', text)
                yesterday_match = re.search(r'Y:\s*(\d+(?:,\d+)*)', text)
                db_match = re.search(r'DB:\s*(\d+(?:,\d+)*)', text)
                total_match = re.search(r'Surfed(?:\s+in\s+3\s+Days)?:\s*(\d+(?:,\d+)*)', text)
                
                today = int(today_match.group(1).replace(',', '')) if today_match else 0
                yesterday = int(yesterday_match.group(1).replace(',', '')) if yesterday_match else 0
                day_before = int(db_match.group(1).replace(',', '')) if db_match else 0
                
                if total_match:
                    total = int(total_match.group(1).replace(',', ''))
                else:
                    total = today + yesterday + day_before
                
                leaderboard.append({
                    'rank': rank,
                    'user_id': user_id,
                    'total_surfed': total,
                    'today_credits': today,
                    'yesterday_credits': yesterday,
                    'day_before_credits': day_before
                })
                rank += 1
            
            return leaderboard
        except Exception as e:
            return []
    
    @staticmethod
    def parse(html: str) -> List[Dict]:
        leaderboard = LeaderboardParser.parse_with_beautifulsoup(html)
        leaderboard.sort(key=lambda x: x['rank'])
        return leaderboard

def fetch_leaderboard() -> Optional[List[Dict]]:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Cookie': CONFIG['cookies']
        }
        
        response = requests.post(
            CONFIG['leaderboard_url'],
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            leaderboard = LeaderboardParser.parse(response.text)
            if leaderboard:
                return leaderboard
        return None
            
    except Exception as e:
        logger.error(f"Network error: {e}")
        return None

def calculate_target(leaderboard: List[Dict]) -> Tuple[int, str]:
    if len(leaderboard) < 2:
        return 0, "Not enough data"
    
    second_place = leaderboard[1]
    
    if state.strategy == 'today_only':
        target = second_place['today_credits'] + state.safety_margin
        explanation = f"2nd today ({second_place['today_credits']}) + {state.safety_margin}"
    else:
        second_combined = second_place['today_credits'] + second_place['yesterday_credits']
        target = second_combined + state.safety_margin
        explanation = f"2nd combined ({second_combined}) + {state.safety_margin}"
    
    return target, explanation

def get_my_value(my_data: Dict) -> int:
    if state.strategy == 'today_only':
        return my_data['today_credits']
    else:
        return my_data['today_credits'] + my_data['yesterday_credits']

def send_telegram_message(message: str, image_data=None):
    if not CONFIG.get('chat_id'):
        return
    
    try:
        url = f"https://api.telegram.org/bot{CONFIG['telegram_token']}/sendMessage"
        data = {'chat_id': CONFIG['chat_id'], 'text': message, 'parse_mode': 'HTML'}
        requests.post(url, data=data, timeout=15)
        
        if image_data:
            url = f"https://api.telegram.org/bot{CONFIG['telegram_token']}/sendPhoto"
            files = {'photo': ('screenshot.png', image_data, 'image/png')}
            data = {'chat_id': CONFIG['chat_id']}
            requests.post(url, files=files, data=data, timeout=15)
    except Exception as e:
        logger.error(f"Telegram error: {e}")

def check_competition_status():
    """Single competition check"""
    current_time = datetime.now()
    state.last_check_time = current_time
    
    leaderboard = fetch_leaderboard()
    if not leaderboard:
        logger.error("Failed to fetch leaderboard")
        if state.driver and not state.is_logged_in:
            force_login(state.driver)
        return
    
    state.leaderboard = leaderboard
    
    # Find my position
    my_data = None
    for entry in state.leaderboard:
        if entry['user_id'] == CONFIG['my_user_id']:
            my_data = entry
            state.my_position = entry['rank']
            break
    
    if not my_data:
        logger.error(f"User #{CONFIG['my_user_id']} not in top 10!")
        return
    
    my_value = get_my_value(my_data)
    
    # Growth rate calculation
    if state.last_my_credits > 0 and state.last_credits_time:
        time_diff_hours = (current_time - state.last_credits_time).total_seconds() / 3600.0
        credits_gained = my_value - state.last_my_credits
        
        if credits_gained > 0 and time_diff_hours > 0:
            state.credits_growth_rate = credits_gained / time_diff_hours
    
    state.last_my_credits = my_value
    state.last_credits_time = current_time
    
    # Competition logic
    status_message = ""
    if state.my_position != 1:
        status_message = f"📉 Currently #{state.my_position}, chasing #1"
        state.target_achieved = False
    else:
        target, explanation = calculate_target(state.leaderboard)
        state.current_target = target
        
        if my_value >= target:
            status_message = f"✅ TARGET ACHIEVED! Position #1 secured"
            state.target_achieved = True
        else:
            gap = target - my_value
            status_message = f"🏃 CHASING TARGET - Need {gap} more credits"
            state.target_achieved = False
    
    # Send status to Telegram
    full_message = f"""
🔄 <b>Competition Update</b>
🏆 Position: <b>#{state.my_position}</b>
📊 My Credits: <b>{my_value}</b>
📈 Growth Rate: <b>{state.credits_growth_rate:.1f}/hour</b>

{status_message}
    """.strip()
    
    send_telegram_message(full_message)
    
    # Take screenshot if browser is active
    if state.driver and state.browser_active:
        screenshot_data = take_screenshot(state.driver, "status_check", "Competition Status")
        if screenshot_data:
            send_telegram_message("📸 Current browser state:", screenshot_data)

def telegram_bot_loop():
    """Handle Telegram commands"""
    last_update_id = 0
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{CONFIG['telegram_token']}/getUpdates?timeout=30"
            response = requests.get(url, timeout=35)
            if response.status_code == 200:
                updates = response.json()
                if updates and 'result' in updates:
                    for update in updates['result']:
                        update_id = update['update_id']
                        if update_id > last_update_id:
                            last_update_id = update_id
                            if 'message' in update and 'text' in update['message']:
                                command = update['message']['text']
                                chat_id = update['message']['chat']['id']
                                CONFIG['chat_id'] = chat_id
                                
                                if command == '/start':
                                    state.is_running = True
                                    send_telegram_message("✅ Monitor STARTED!")
                                    check_competition_status()
                                elif command == '/stop':
                                    state.is_running = False
                                    send_telegram_message("⏹️ Monitor STOPPED!")
                                elif command == '/status':
                                    check_competition_status()
                                elif command == '/screenshot':
                                    if state.driver and state.browser_active:
                                        screenshot_data = take_screenshot(state.driver, "telegram_request", "Telegram Screenshot")
                                        if screenshot_data:
                                            send_telegram_message("📸 Browser screenshot:", screenshot_data)
                                        else:
                                            send_telegram_message("❌ Could not take screenshot")
                                    else:
                                        send_telegram_message("❌ Browser not active")
                                elif command == '/login':
                                    if state.driver:
                                        if force_login(state.driver):
                                            send_telegram_message("✅ Login successful!")
                                        else:
                                            send_telegram_message("❌ Login failed")
        except Exception as e:
            logger.error(f"Telegram bot error: {e}")
        
        time.sleep(10)

def initialize_system():
    """Initialize the complete system"""
    logger.info("Initializing system...")
    
    # Setup browser
    driver = setup_browser()
    if not driver:
        logger.error("Failed to setup browser")
        return False
    
    state.driver = driver
    state.browser_active = True
    
    # Login
    if not force_login(driver):
        logger.error("Failed to login")
        return False
    
    logger.info("System initialized successfully!")
    return True

def main_loop():
    """Main monitoring loop"""
    logger.info("Starting AdShare Monitor...")
    
    # Initialize system
    if not initialize_system():
        logger.error("System initialization failed!")
        return
    
    send_telegram_message("🚀 AdShare Monitor Started!")
    
    if CONFIG['auto_start']:
        state.is_running = True
        check_competition_status()
    
    last_check = datetime.now()
    
    while True:
        try:
            if state.is_running:
                current_time = datetime.now()
                if (current_time - last_check).total_seconds() >= CONFIG['leaderboard_check_interval']:
                    check_competition_status()
                    last_check = current_time
                
                # Keep browser alive by refreshing periodically
                if state.driver and state.browser_active:
                    try:
                        current_url = state.driver.current_url
                        if "adsha.re" not in current_url:
                            state.driver.get(CONFIG['browser_url'])
                            time.sleep(5)
                    except:
                        pass
                
            time.sleep(30)
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(30)

def signal_handler(sig, frame):
    logger.info("Shutdown signal received")
    if state.driver:
        state.driver.quit()
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start Telegram bot in background
    import threading
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()
    
    main_loop()
