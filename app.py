#!/usr/bin/env python3
"""
AdShare Monitor v7.0 - Simplified & Fixed Leaderboard
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
    from selenium.webdriver.common.action_chains import ActionChains
    from PIL import Image
except ImportError:
    print("Installing required packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", 
                   "selenium", "requests", "beautifulsoup4", "pytz", 
                   "Pillow"], check=True)
    import requests
    from bs4 import BeautifulSoup
    import pytz
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
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
    'competition_strategy': 'today_only',  # 'today_only' or 'combined'
    'my_user_id': '4242',
    
    # Browser Settings
    'browser_url': "https://adsha.re/surf",
    'headless_mode': True,
    
    # Technical Settings
    'leaderboard_url': 'https://adsha.re/ten',
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
        self.competitor_history = {}  # Track competitor performance

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
        
        with open(path, 'rb') as f:
            image_data = f.read()
        
        logger.info(f"Screenshot: {description or name}")
        return image_data
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return None

def install_userscript_properly(driver):
    """The CORRECT way - handle new window!"""
    logger.info("Starting userscript installation...")
    
    try:
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
                actions = ActionChains(driver)
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
    options.set_preference("xpinstall.signatures.required", False)
    options.set_preference("extensions.autoDisableScopes", 0)
    options.set_preference("extensions.enabledScopes", 15)
    
    # Create driver
    try:
        driver = webdriver.Firefox(options=options)
        logger.info("Firefox browser started successfully")
    except Exception as e:
        logger.error(f"Failed to start Firefox: {e}")
        return None
    
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
    """EXACT WORKING LOGIN - No changes from working version"""
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

# ==================== FIXED LEADERBOARD PARSING ====================

class LeaderboardParser:
    @staticmethod
    def parse_leaderboard(html: str) -> List[Dict]:
        """Parse leaderboard from exact HTML format"""
        leaderboard = []
        
        try:
            # Extract all entries with the specific pattern
            pattern = r'<div style=\'width:250px; margin:5px auto; position:relative\'>.*?#(\d+).*?Surfed.*?(\d+).*?T:\s*([\d,]+).*?Y:\s*([\d,]+).*?DB:\s*([\d,]+)'
            matches = re.findall(pattern, html, re.DOTALL)
            
            rank = 1
            for match in matches:
                user_id, surfed, today, yesterday, day_before = match
                
                leaderboard.append({
                    'rank': rank,
                    'user_id': user_id,
                    'total_surfed': int(surfed.replace(',', '')),
                    'today_credits': int(today.replace(',', '')),
                    'yesterday_credits': int(yesterday.replace(',', '')),
                    'day_before_credits': int(day_before.replace(',', ''))
                })
                rank += 1
                
        except Exception as e:
            logger.error(f"Error parsing leaderboard: {e}")
            
        return leaderboard

def fetch_leaderboard() -> Optional[List[Dict]]:
    """Fetch leaderboard with exact headers from curl"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'upgrade-insecure-requests': '1',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-dest': 'iframe',
            'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'referer': 'https://adsha.re/surf',
            'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        response = requests.post(
            CONFIG['leaderboard_url'],
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            leaderboard = LeaderboardParser.parse_leaderboard(response.text)
            if leaderboard:
                logger.info(f"Successfully parsed {len(leaderboard)} leaderboard entries")
                return leaderboard
        return None
            
    except Exception as e:
        logger.error(f"Network error: {e}")
        return None

# ==================== COMPETITION LOGIC ====================

def calculate_target(leaderboard: List[Dict]) -> Tuple[int, str]:
    if len(leaderboard) < 2:
        return 0, "Not enough data"
    
    second_place = leaderboard[1]
    
    if state.strategy == 'today_only':
        target = second_place['today_credits'] + state.safety_margin
        explanation = f"2nd today ({second_place['today_credits']}) + {state.safety_margin}"
    else:
        # For combined strategy, target is 2nd place's combined but we track our today only
        second_combined = second_place['today_credits'] + second_place['yesterday_credits']
        target = second_combined + state.safety_margin
        explanation = f"2nd combined ({second_combined}) + {state.safety_margin}"
    
    return target, explanation

def get_my_value(my_data: Dict) -> int:
    """Always return today's credits only"""
    return my_data['today_credits']

def track_competitor_performance(leaderboard: List[Dict]):
    """Track competitor performance metrics"""
    current_time = datetime.now()
    
    for entry in leaderboard[:3]:  # Track top 3 competitors
        user_id = entry['user_id']
        today_credits = entry['today_credits']
        
        if user_id not in state.competitor_history:
            state.competitor_history[user_id] = {
                'credits': [],
                'timestamps': [],
                'last_credits': today_credits,
                'last_update': current_time
            }
        else:
            history = state.competitor_history[user_id]
            time_diff = (current_time - history['last_update']).total_seconds() / 3600.0
            
            if time_diff > 0 and today_credits > history['last_credits']:
                credits_gained = today_credits - history['last_credits']
                rate = credits_gained / time_diff
                
                history['credits'].append(credits_gained)
                history['timestamps'].append(current_time)
                history['last_credits'] = today_credits
                history['last_update'] = current_time
                
                # Keep only last 24 hours of data
                cutoff_time = current_time - timedelta(hours=24)
                history['credits'] = [c for i, c in enumerate(history['credits']) 
                                    if history['timestamps'][i] > cutoff_time]
                history['timestamps'] = [t for t in history['timestamps'] if t > cutoff_time]

def get_competitor_metrics(leaderboard: List[Dict]) -> str:
    """Get competitor performance metrics"""
    if len(leaderboard) < 2:
        return ""
    
    metrics = []
    current_time = datetime.now()
    
    for entry in leaderboard[:3]:  # Top 3 competitors
        user_id = entry['user_id']
        if user_id in state.competitor_history:
            history = state.competitor_history[user_id]
            if history['credits']:
                avg_rate = sum(history['credits']) / len(history['credits'])
                last_active = history['last_update'].strftime('%H:%M')
                time_since = (current_time - history['last_update']).total_seconds() / 3600.0
                
                metrics.append(
                    f"#{user_id}: {avg_rate:.1f}/hr, active {last_active} "
                    f"({time_since:.1f}h ago)"
                )
    
    return "\n".join(metrics) if metrics else "No competitor data yet"

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
    
    # Track performance
    track_competitor_performance(leaderboard)
    
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
        first_place = leaderboard[0]
        gap = first_place['today_credits'] - my_value
        status_message = f"📉 Currently #{state.my_position}, gap: {gap} credits"
        state.target_achieved = False
    else:
        target, explanation = calculate_target(leaderboard)
        state.current_target = target
        
        if my_value >= target:
            status_message = f"✅ TARGET ACHIEVED! Position #1 secured"
            state.target_achieved = True
        else:
            gap = target - my_value
            status_message = f"🏃 CHASING TARGET - Need {gap} more credits"
            state.target_achieved = False
    
    # Get competitor metrics
    competitor_metrics = get_competitor_metrics(leaderboard)
    
    # Send status to Telegram
    full_message = f"""
<b>Competition Update</b>
🏆 Position: <b>#{state.my_position}</b>
📊 My Credits Today: <b>{my_value}</b>
📈 My Rate: <b>{state.credits_growth_rate:.1f}/hour</b>

{status_message}

<b>Competitor Activity:</b>
{competitor_metrics if competitor_metrics else "No data yet"}
    """.strip()
    
    send_telegram_message(full_message)

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
                                elif command == '/today_only':
                                    state.strategy = 'today_only'
                                    send_telegram_message("🎯 Strategy set to: TODAY ONLY")
                                    check_competition_status()
                                elif command == '/combined':
                                    state.strategy = 'combined'
                                    send_telegram_message("🎯 Strategy set to: COMBINED")
                                    check_competition_status()
                                elif command.startswith('/margin '):
                                    try:
                                        new_margin = int(command.split()[1])
                                        state.safety_margin = new_margin
                                        send_telegram_message(f"🎯 Safety margin set to: {new_margin}")
                                        check_competition_status()
                                    except:
                                        send_telegram_message("❌ Usage: /margin <number>")
                                elif command == '/settings':
                                    settings_msg = f"""
<b>Current Settings:</b>
Strategy: {state.strategy}
Safety Margin: {state.safety_margin}
Check Interval: {CONFIG['leaderboard_check_interval']//60} minutes
My User ID: {CONFIG['my_user_id']}
                                    """.strip()
                                    send_telegram_message(settings_msg)
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
                
                # Keep browser alive
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
