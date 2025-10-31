#!/usr/bin/env python3
"""
AdShare Monitor v9.1 - Fixed Telegram & Screenshot
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
    'telegram_token': "8332516699:AAF8287h5Be4ejvhoFpcYiHG4YHVJlH_R0g",  # FIXED: Correct spelling
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
        self.firefox_process = None
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
        self.competitor_history = {}
        self.profile_initialized = False

state = MonitorState()

# ==================== SELENIUM SETUP (ONLY FOR FIRST TIME) ====================

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

def install_userscript_properly(driver):
    """EXACT SAME METHOD from working script"""
    logger.info("Starting userscript installation...")
    
    try:
        main_window = driver.current_window_handle
        initial_windows = driver.window_handles
        
        logger.info("Opening Greasyfork page...")
        driver.get(USERSCRIPT_PAGE)
        time.sleep(6)
        
        page_source = driver.page_source
        if "install this script" not in page_source.lower():
            logger.error("Violentmonkey not detected by Greasyfork!")
            return False
        
        logger.info("Violentmonkey detected!")
        
        logger.info("Clicking install link...")
        try:
            install_link = driver.find_element(By.CSS_SELECTOR, "a.install-link")
            install_link.click()
            logger.info("Clicked install link")
        except Exception as e:
            logger.warning(f"Direct click failed, trying JS: {e}")
            driver.execute_script("document.querySelector('a.install-link').click();")
            logger.info("JS click executed")
        
        time.sleep(5)
        
        current_windows = driver.window_handles
        
        if len(current_windows) > len(initial_windows):
            logger.info("New window detected!")
            
            new_window = [w for w in current_windows if w not in initial_windows][-1]
            driver.switch_to.window(new_window)
            
            time.sleep(3)
            
            logger.info("Looking for Install button...")
            
            install_selectors = [
                (By.XPATH, "//button[contains(text(), 'Install')]"),
                (By.XPATH, "//button[contains(@class, 'install')]"),
                (By.CSS_SELECTOR, "button.vm-confirm"),
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//input[@type='submit']"),
            ]
            
            installed = False
            for by, selector in install_selectors:
                try:
                    install_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    
                    driver.execute_script("arguments[0].scrollIntoView(true);", install_btn)
                    time.sleep(1)
                    
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
            
            time.sleep(2)
            remaining_windows = driver.window_handles
            
            if len(remaining_windows) < len(current_windows):
                logger.info("Dialog window closed - likely installed successfully!")
            else:
                logger.info("Dialog still open")
            
            if main_window in driver.window_handles:
                driver.switch_to.window(main_window)
            else:
                driver.switch_to.window(driver.window_handles[0])
            
            logger.info("Userscript installation completed!")
            return True
            
        else:
            logger.error("No new window opened!")
            return False
            
    except Exception as e:
        logger.error(f"Error during installation: {e}")
        try:
            driver.switch_to.window(main_window)
        except:
            if driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
        return False

def initialize_profile_with_selenium():
    """Use Selenium ONLY ONCE to install extensions and userscript"""
    if state.profile_initialized:
        logger.info("Profile already initialized")
        return True
        
    logger.info("🚀 INITIALIZING PROFILE WITH SELENIUM (ONE-TIME SETUP)")
    
    # Clean and create profile directory
    if os.path.exists(CONFIG['profile_dir']):
        import shutil
        shutil.rmtree(CONFIG['profile_dir'])
    os.makedirs(CONFIG['profile_dir'])
    
    # Download extensions
    extension_paths = download_files()
    
    # Firefox options for Selenium
    options = Options()
    if CONFIG['headless_mode']:
        options.add_argument("--headless")
    options.add_argument(f"-profile")
    options.add_argument(CONFIG['profile_dir'])
    options.set_preference("xpinstall.signatures.required", False)
    options.set_preference("extensions.autoDisableScopes", 0)
    options.set_preference("extensions.enabledScopes", 15)
    
    # STEP 1: Install Extensions
    logger.info("📦 STEP 1: Installing Extensions with Selenium...")
    
    driver = None
    try:
        driver = webdriver.Firefox(options=options)
        driver.set_window_size(1400, 1000)
        
        for ext_id, ext_path in extension_paths.items():
            abs_path = os.path.abspath(ext_path)
            driver.install_addon(abs_path, temporary=False)
            logger.info(f"✅ Installed {EXTENSIONS[ext_id]['name']}")
            time.sleep(3)
        
        logger.info("🔄 Restarting browser to load extensions...")
        driver.quit()
        driver = None
        
    except Exception as e:
        logger.error(f"❌ Error installing extensions: {e}")
        if driver:
            driver.quit()
        return False
    
    # STEP 2: Install Userscript
    logger.info("📝 STEP 2: Installing Userscript with Selenium...")
    
    time.sleep(3)
    try:
        driver = webdriver.Firefox(options=options)
        driver.set_window_size(1400, 1000)
        
        logger.info("⏳ Waiting for extensions to load...")
        time.sleep(10)
        
        # Install userscript
        success = install_userscript_properly(driver)
        
        if success:
            logger.info("✅ Userscript installation completed!")
        else:
            logger.error("❌ Userscript installation failed")
        
        # Clean up Selenium
        driver.quit()
        driver = None
        
        state.profile_initialized = True
        state.extensions_installed = True
        logger.info("🎉 PROFILE INITIALIZATION COMPLETE! Selenium will not be used again.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error installing userscript: {e}")
        if driver:
            driver.quit()
        return False

# ==================== LIGHTWEIGHT FIREFOX MANAGEMENT ====================

def start_firefox_lightweight():
    """Start Firefox without Selenium (lightweight)"""
    if not state.profile_initialized:
        logger.info("Profile not initialized, running one-time setup...")
        if not initialize_profile_with_selenium():
            return False
    
    logger.info("🚀 Starting Firefox in lightweight mode...")
    
    try:
        # Start Firefox directly without Selenium
        firefox_cmd = [
            'firefox',
            '-profile', CONFIG['profile_dir'],
            '-width', '1400',
            '-height', '1000',
            '-new-tab', CONFIG['browser_url']
        ]
        
        if CONFIG['headless_mode']:
            # Use XVFB for headless mode
            display_cmd = ['Xvfb', ':99', '-screen', '0', '1400x1000x24', '-ac']
            display_process = subprocess.Popen(display_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            
            os.environ['DISPLAY'] = ':99'
            firefox_process = subprocess.Popen(firefox_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            firefox_process = subprocess.Popen(firefox_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        state.firefox_process = firefox_process
        state.browser_active = True
        
        logger.info("✅ Firefox started successfully in lightweight mode!")
        logger.info("💡 Note: Login will be handled by userscript automatically")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to start Firefox: {e}")
        return False

def stop_firefox_lightweight():
    """Stop Firefox process"""
    if state.firefox_process:
        try:
            state.firefox_process.terminate()
            state.firefox_process.wait(timeout=10)
            logger.info("✅ Firefox stopped")
        except:
            try:
                state.firefox_process.kill()
                logger.info("✅ Firefox force stopped")
            except:
                pass
        state.firefox_process = None
    
    state.browser_active = False

def take_screenshot_lightweight():
    """Take screenshot using scrot"""
    try:
        os.makedirs(CONFIG['screenshots_dir'], exist_ok=True)
        path = f"{CONFIG['screenshots_dir']}/screenshot_{int(time.time())}.png"
        
        # Use scrot for screenshot
        screenshot_cmd = ['scrot', path]
        result = subprocess.run(screenshot_cmd, capture_output=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(path):
            with open(path, 'rb') as f:
                image_data = f.read()
            logger.info("✅ Screenshot taken")
            return image_data
        else:
            logger.warning("⚠️ Could not take screenshot")
            return None
            
    except Exception as e:
        logger.error(f"❌ Screenshot error: {e}")
        return None

# ==================== LEADERBOARD & COMPETITION LOGIC ====================

class LeaderboardParser:
    @staticmethod
    def parse_with_beautifulsoup(html: str) -> List[Dict]:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            leaderboard = []
            
            entries = soup.find_all('div', style=lambda x: x and 'width:250px' in x and 'margin:5px auto' in x)
            
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
                
                today = int(today_match.group(1).replace(',', '')) if today_match else 0
                yesterday = int(yesterday_match.group(1).replace(',', '')) if yesterday_match else 0
                day_before = int(db_match.group(1).replace(',', '')) if db_match else 0
                
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
            
            logger.info(f"✅ Parsed {len(leaderboard)} leaderboard entries")
            return leaderboard
        except Exception as e:
            logger.error(f"❌ Error parsing leaderboard: {e}")
            return []

def fetch_leaderboard_fixed() -> Optional[List[Dict]]:
    """Fetch leaderboard with exact headers"""
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
            'Cookie': 'adshare_e=bonna.b.o.rre.z%40gmail.com; adshare_s=e4dc9d210bb38a86cd360253a82feb2cc6ed84f5ddf778be89484fb476998e0dfc31280c575a38a2467067cd6ec1d6ff7e25aa46dedd6ea454831df26365dfc2; adshare_d=20251025; adshare_h=https%3A%2F%2Fadsha.re%2Faffiliates'
        }
        
        response = requests.post(
            CONFIG['leaderboard_url'],
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            leaderboard = LeaderboardParser.parse_with_beautifulsoup(response.text)
            if leaderboard:
                return leaderboard
        return None
            
    except Exception as e:
        logger.error(f"❌ Network error fetching leaderboard: {e}")
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
        target = second_combined
        explanation = f"2nd combined today+yesterday ({second_combined})"
    
    return target, explanation

def get_my_value(my_data: Dict) -> int:
    return my_data['today_credits']

def should_stop_browser(leaderboard: List[Dict]) -> bool:
    if state.my_position != 1:
        return False
    
    my_data = None
    for entry in leaderboard:
        if entry['user_id'] == CONFIG['my_user_id']:
            my_data = entry
            break
    
    if not my_data:
        return False
    
    my_today = get_my_value(my_data)
    target, _ = calculate_target(leaderboard)
    
    return my_today >= target

def send_telegram_message(message: str, image_data=None):
    if not CONFIG.get('chat_id'):
        logger.info(f"Telegram message (no chat_id): {message[:100]}...")
        return
    
    try:
        url = f"https://api.telegram.org/bot{CONFIG['telegram_token']}/sendMessage"  # FIXED: Correct spelling
        data = {'chat_id': CONFIG['chat_id'], 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, data=data, timeout=15)
        
        if image_data:
            url = f"https://api.telegram.org/bot{CONFIG['telegram_token']}/sendPhoto"  # FIXED: Correct spelling
            files = {'photo': ('screenshot.png', image_data, 'image/png')}
            data = {'chat_id': CONFIG['chat_id']}
            requests.post(url, files=files, data=data, timeout=15)
            
        logger.info(f"📤 Telegram message sent: {message[:100]}...")
    except Exception as e:
        logger.error(f"❌ Telegram error: {e}")

def check_competition_status():
    """Competition check without Selenium"""
    current_time = datetime.now()
    state.last_check_time = current_time
    
    leaderboard = fetch_leaderboard_fixed()
    if not leaderboard:
        logger.error("❌ Failed to fetch leaderboard")
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
        logger.error(f"❌ User #{CONFIG['my_user_id']} not in top 10!")
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
    
    # Browser control logic
    should_stop = should_stop_browser(leaderboard)
    
    if should_stop and state.browser_active:
        logger.info("🎯 Target achieved, stopping Firefox...")
        stop_firefox_lightweight()
        send_telegram_message("🎯 <b>TARGET ACHIEVED!</b> Firefox stopped.")
    elif not should_stop and not state.browser_active and state.is_running:
        logger.info("🏃 Need to chase target, starting Firefox...")
        start_firefox_lightweight()
    
    # Competition status
    target, explanation = calculate_target(leaderboard)
    state.current_target = target
    
    status_message = ""
    if state.my_position != 1:
        first_place = leaderboard[0]
        gap = first_place['today_credits'] - my_value
        status_message = f"📉 Currently #{state.my_position}, chasing #1 (gap: {gap})"
    else:
        if my_value >= target:
            status_message = f"✅ TARGET ACHIEVED! Position #1 secured"
        else:
            gap = target - my_value
            status_message = f"🏃 CHASING TARGET - Need {gap} more credits"
    
    # Performance report
    performance_report = f"📈 My Speed: {state.credits_growth_rate:.1f} surf/hour\n"
    performance_report += f"🖥️ Firefox: {'RUNNING' if state.browser_active else 'STOPPED'}\n"
    performance_report += f"💾 Mode: {'LIGHTWEIGHT' if state.profile_initialized else 'SETUP'}"
    
    # Send status to Telegram
    full_message = f"""
🔄 <b>Competition Update</b>
🏆 Position: <b>#{state.my_position}</b>
📊 My Credits Today: <b>{my_value}</b>
🎯 Target: <b>{target}</b> ({explanation})
🎯 Strategy: <b>{state.strategy.upper()}</b>

{status_message}

{performance_report}
    """.strip()
    
    send_telegram_message(full_message)

def telegram_bot_loop():
    """Telegram bot without Selenium dependencies"""
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
                                    if not state.browser_active:
                                        start_firefox_lightweight()
                                    check_competition_status()
                                elif command == '/stop':
                                    state.is_running = False
                                    stop_firefox_lightweight()
                                    send_telegram_message("⏹️ Monitor STOPPED!")
                                elif command == '/status':
                                    check_competition_status()
                                elif command == '/screenshot':
                                    screenshot_data = take_screenshot_lightweight()
                                    if screenshot_data:
                                        send_telegram_message("📸 Firefox screenshot:", screenshot_data)
                                    else:
                                        send_telegram_message("❌ Could not take screenshot")
                                elif command == '/strategy_today':
                                    state.strategy = 'today_only'
                                    send_telegram_message("🎯 Strategy set to: TODAY ONLY\nTarget = 2nd today + safety margin")
                                    check_competition_status()
                                elif command == '/strategy_combined':
                                    state.strategy = 'combined'
                                    send_telegram_message("🎯 Strategy set to: COMBINED\nTarget = 2nd (today + yesterday)")
                                    check_competition_status()
                                elif command.startswith('/margin '):
                                    try:
                                        new_margin = int(command.split()[1])
                                        state.safety_margin = new_margin
                                        send_telegram_message(f"🛡️ Safety margin set to: {new_margin}")
                                        check_competition_status()
                                    except:
                                        send_telegram_message("❌ Usage: /margin <number>")
                                elif command == '/setup_profile':
                                    send_telegram_message("🔄 Running one-time profile setup...")
                                    if initialize_profile_with_selenium():
                                        send_telegram_message("✅ Profile setup completed!")
                                    else:
                                        send_telegram_message("❌ Profile setup failed!")
                                elif command == '/help':
                                    help_text = """
🤖 <b>AdShare Monitor (Lightweight)</b>

<b>Basic Controls</b>
/start - Start monitoring & Firefox
/stop - Stop monitoring & Firefox
/status - Check current status
/screenshot - Take screenshot

<b>Strategy Settings</b>
/strategy_today - Target = 2nd today + safety margin
/strategy_combined - Target = 2nd (today + yesterday)
/margin <number> - Set safety margin

<b>Technical</b>
/setup_profile - Run one-time profile setup
/help - Show this help

<b>Current Status</b>
Strategy: {strategy}
Safety Margin: {margin}
Firefox: {browser_status}
Mode: {mode}
                                    """.format(
                                        strategy=state.strategy.upper(),
                                        margin=state.safety_margin,
                                        browser_status='RUNNING' if state.browser_active else 'STOPPED',
                                        mode='LIGHTWEIGHT' if state.profile_initialized else 'SETUP'
                                    )
                                    send_telegram_message(help_text)
        except Exception as e:
            logger.error(f"❌ Telegram bot error: {e}")
        
        time.sleep(10)

def main_loop():
    """Main loop without Selenium"""
    logger.info("🚀 Starting AdShare Monitor (Lightweight Mode)...")
    
    # Check if profile needs initialization
    if not state.profile_initialized:
        logger.info("📦 First run: Profile needs initialization")
        if initialize_profile_with_selenium():
            send_telegram_message("✅ Profile setup completed! Now running in lightweight mode.")
        else:
            send_telegram_message("❌ Profile setup failed! Use /setup_profile to retry.")
            return
    
    send_telegram_message("🚀 AdShare Monitor Started!")
    
    if CONFIG['auto_start']:
        state.is_running = True
        start_firefox_lightweight()
        time.sleep(10)  # Wait for Firefox to start
        check_competition_status()
    
    last_check = datetime.now()
    
    while True:
        try:
            if state.is_running:
                current_time = datetime.now()
                if (current_time - last_check).total_seconds() >= CONFIG['leaderboard_check_interval']:
                    check_competition_status()
                    last_check = current_time
                
            time.sleep(30)
                
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down...")
            break
        except Exception as e:
            logger.error(f"❌ Main loop error: {e}")
            time.sleep(30)

def signal_handler(sig, frame):
    logger.info("🛑 Shutdown signal received")
    stop_firefox_lightweight()
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    import threading
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()
    
    main_loop()
