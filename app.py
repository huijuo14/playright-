#!/usr/bin/env python3
"""
AdShare Monitor v8.0 - Railway Edition with Fixed Profile Loading
"""

import asyncio
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
import tarfile
import zipfile
import shutil

try:
    import requests
    from bs4 import BeautifulSoup
    import pytz
    from playwright.async_api import async_playwright
    import asyncio
except ImportError:
    print("Installing required packages...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "requests", "beautifulsoup4", "pytz",
        "playwright", "urllib3", "asyncio"
    ], check=True)
    import requests
    from bs4 import BeautifulSoup
    import pytz
    from playwright.async_api import async_playwright
    import asyncio

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
    'browser_width': 1280,
    'browser_height': 720,
    'headless_mode': True,
    
    # Profile Settings - UPDATED ZIP URL
    'firefox_profile_url': "https://github.com/huijuo14/playright-/releases/download/v1/firefox-profile-backup.zip",
    'profile_name': "firefox-profile",  # Updated profile name
    
    # Technical Settings
    'leaderboard_url': 'https://adsha.re/ten',
    'cookies': 'adshare_e=bonna.b.o.rre.z%40gmail.com; adshare_s=e4dc9d210bb38a86cd360253a82feb2cc6ed84f5ddf778be89484fb476998e0dfc31280c575a38a2467067cd6ec1d6ff7e25aa46dedd6ea454831df26365dfc2; adshare_d=20251025; adshare_h=https%3A%2F%2Fadsha.re%2Faffiliates',
    'timezone': 'Asia/Kolkata',
    
    # Auto Start
    'auto_start': True,
}

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== FIREFOX PROFILE MANAGEMENT ====================

class FirefoxProfileManager:
    def __init__(self):
        self.profile_path = Path.home() / '.mozilla' / 'firefox'
        self.target_profile_name = CONFIG['profile_name']
        
    def download_and_extract_profile(self):
        """Download and extract Firefox profile from GitHub releases - ZIP VERSION"""
        try:
            backup_url = CONFIG['firefox_profile_url']
            backup_file = "firefox_profile_backup.zip"
            
            logger.info(f"📥 Downloading Firefox profile from {backup_url}")
            
            # Download the profile backup
            urllib.request.urlretrieve(backup_url, backup_file)
            
            if not os.path.exists(backup_file):
                logger.error("❌ Failed to download profile backup")
                return False
            
            # Ensure firefox directory exists
            self.profile_path.mkdir(parents=True, exist_ok=True)
            
            # Extract the ZIP file
            logger.info("📦 Extracting Firefox profile from ZIP...")
            with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                # Get list of files
                file_list = zip_ref.namelist()
                logger.info(f"📁 ZIP contains {len(file_list)} items")
                
                # Extract everything to firefox directory
                zip_ref.extractall(self.profile_path)
            
            # Clean up
            os.remove(backup_file)
            
            logger.info("✅ Firefox profile extraction completed")
            
            # Verify extraction
            extracted_profile = self.find_extracted_profile()
            if extracted_profile:
                logger.info(f"✅ Profile verified: {extracted_profile}")
                return True
            else:
                logger.error("❌ Profile extraction failed - no profile found after extraction")
                return False
            
        except Exception as e:
            logger.error(f"❌ Profile setup failed: {e}")
            return False
    
    def find_extracted_profile(self):
        """Find the extracted profile directory"""
        try:
            # Look for the exact profile name
            target_path = self.profile_path / self.target_profile_name
            if target_path.exists():
                logger.info(f"✅ Found exact profile: {target_path}")
                return str(target_path)
            
            # Look for any directory containing the profile name
            for item in self.profile_path.iterdir():
                if item.is_dir() and self.target_profile_name in item.name:
                    logger.info(f"✅ Found profile directory: {item}")
                    return str(item)
            
            # Look for any directory that might be a Firefox profile
            for item in self.profile_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Check if it has Firefox profile files
                    profile_files = ['prefs.js', 'places.sqlite', 'cookies.sqlite']
                    has_profile_files = any((item / f).exists() for f in profile_files)
                    if has_profile_files:
                        logger.info(f"✅ Found potential profile: {item}")
                        return str(item)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Profile search failed: {e}")
            return None
    
    def setup_profile_for_playwright(self):
        """Setup profile for Playwright use"""
        try:
            profile_dir = self.find_extracted_profile()
            
            if not profile_dir:
                logger.info("🔄 Profile not found locally, downloading...")
                if self.download_and_extract_profile():
                    profile_dir = self.find_extracted_profile()
            
            if not profile_dir:
                logger.error("❌ Could not find or download profile directory")
                return None
            
            # For Playwright, we need to use the profile directory directly
            logger.info(f"🎯 Using profile directory: {profile_dir}")
            return profile_dir
            
        except Exception as e:
            logger.error(f"❌ Profile setup for Playwright failed: {e}")
            return None

# ==================== PLAYWRIGHT BROWSER MANAGER ====================

class PlaywrightBrowser:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.context = None
        self.state = {
            'is_logged_in': False,
            'browser_active': False,
            'last_activity': None
        }
        self.profile_manager = FirefoxProfileManager()
        
    async def setup_playwright(self):
        """Setup Playwright with Firefox profile"""
        try:
            logger.info("🚀 Starting Firefox with Playwright...")
            
            self.playwright = await async_playwright().start()
            
            # Get Firefox profile directory
            profile_dir = self.profile_manager.setup_profile_for_playwright()
            
            browser_args = [
                f"--window-size={CONFIG['browser_width']},{CONFIG['browser_height']}",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
            
            if profile_dir:
                logger.info(f"🔧 Launching Firefox with profile: {profile_dir}")
                # Launch with persistent context to use the profile
                self.context = await self.playwright.firefox.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=CONFIG['headless_mode'],
                    args=browser_args,
                    viewport={'width': CONFIG['browser_width'], 'height': CONFIG['browser_height']},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0'
                )
                self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            else:
                logger.warning("⚠️ No profile found, launching fresh Firefox")
                self.browser = await self.playwright.firefox.launch(
                    headless=CONFIG['headless_mode'],
                    args=browser_args
                )
                self.context = await self.browser.new_context(
                    viewport={'width': CONFIG['browser_width'], 'height': CONFIG['browser_height']},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0'
                )
                self.page = await self.context.new_page()
            
            # Stealth mode
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """)
            
            self.state['browser_active'] = True
            self.state['last_activity'] = datetime.now()
            logger.info("✅ Playwright Firefox started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Playwright setup failed: {e}")
            return False
    
    async def smart_delay_async(self, min_delay=2, max_delay=5):
        """Random delay between actions"""
        import random
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"Delaying for {delay:.1f} seconds")
        await asyncio.sleep(delay)
    
    async def detect_page_state(self):
        """Detect current page state"""
        try:
            current_url = self.page.url.lower()
            page_content = await self.page.content()
            
            logger.debug(f"Page detection - URL: {current_url}")
            
            if "adsha.re/login" in current_url:
                return "LOGIN_REQUIRED"
            elif "adsha.re/surf" in current_url:
                content_lower = page_content.lower()
                if "start surfing" in content_lower or "surf now" in content_lower:
                    return "GAME_READY"
                elif "surfing" in content_lower or "earning" in content_lower:
                    return "GAME_ACTIVE"
                else:
                    return "GAME_LOADING"
            elif "adsha.re/dashboard" in current_url:
                return "DASHBOARD"
            else:
                return "UNKNOWN"
        except Exception as e:
            logger.error(f"Page detection error: {e}")
            return f"ERROR: {str(e)}"
    
    async def force_login(self):
        """EXACT WORKING LOGIN FUNCTION - Playwright Version"""
        try:
            logger.info("🚀 STARTING ULTIMATE LOGIN (12+ METHODS)...")
            await self.page.goto("https://adsha.re/login", wait_until='networkidle', timeout=60000)
            await self.page.wait_for_selector("body", timeout=20000)
            await self.smart_delay_async()
            
            page_content = await self.page.content()
            soup = BeautifulSoup(page_content, 'html.parser')
            all_forms = soup.find_all('form')
            logger.info(f"Found {len(all_forms)} forms")
            
            form = soup.find('form', {'name': 'login'})
            if not form:
                logger.warning("No login form found by name, trying first form")
                form = all_forms[0] if all_forms else None
            if not form:
                logger.error("No forms found at all!")
                return False
            
            password_field_name = None
            for field in form.find_all('input'):
                field_name = field.get('name', '')
                field_value = field.get('value', '')
                if field_value == 'Password' and field_name != 'mail' and field_name:
                    password_field_name = field_name
                    logger.info(f"Found password field by value: {password_field_name}")
                    break
            if not password_field_name:
                password_fields = form.find_all('input', {'type': 'password'})
                if password_fields:
                    password_field_name = password_fields[0].get('name')
                    logger.info(f"Found password field by type: {password_field_name}")
            if not password_field_name:
                for field in form.find_all('input'):
                    field_name = field.get('name', '')
                    field_type = field.get('type', '')
                    if field_name and field_name != 'mail' and field_type != 'email':
                        password_field_name = field_name
                        logger.info(f"Found password field by exclusion: {password_field_name}")
                        break
            if not password_field_name:
                inputs = form.find_all('input')
                if len(inputs) >= 2:
                    password_field_name = inputs[1].get('name')
                    logger.info(f"Found password field by position: {password_field_name}")
            if not password_field_name:
                logger.error("Could not find password field by any method")
                return False
            
            logger.info("Filling email (8 methods)...")
            email_selectors = [
                "input[name='mail']",
                "input[type='email']",
                "input[placeholder*='email' i]",
                "input[placeholder*='Email' i]",
                "input[name*='mail' i]",
                "input[name*='email' i]",
                "input:first-of-type",
                "input:nth-of-type(1)"
            ]
            email_filled = False
            for selector in email_selectors:
                try:
                    if await self.page.is_visible(selector):
                        await self.page.fill(selector, "")
                        await self.page.fill(selector, CONFIG['email'])
                        logger.info(f"Email filled with: {selector}")
                        email_filled = True
                        break
                except:
                    continue
            if not email_filled:
                logger.error("All email filling methods failed")
                return False
            
            await self.smart_delay_async()
            
            logger.info("Filling password (6 methods)...")
            password_selectors = [
                f"input[name='{password_field_name}']",
                "input[type='password']",
                "input[placeholder*='password' i]",
                "input[placeholder*='Password' i]",
                "input:nth-of-type(2)",
                "input:last-of-type"
            ]
            password_filled = False
            for selector in password_selectors:
                try:
                    if await self.page.is_visible(selector):
                        await self.page.fill(selector, "")
                        await self.page.fill(selector, CONFIG['password'])
                        logger.info(f"Password filled with: {selector}")
                        password_filled = True
                        break
                except:
                    continue
            if not password_filled:
                logger.error("All password filling methods failed")
                return False
            
            await self.smart_delay_async()
            
            logger.info("Submitting form (12+ methods)...")
            login_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button",
                "input[value*='Login' i]",
                "input[value*='Sign' i]",
                "button:has-text('Login')",
                "button:has-text('Sign')",
                "input[value*='Log']",
                "input[value*='login']",
                "form button",
                "form input[type='submit']",
                "button[class*='login']",
                "button[class*='submit']"
            ]
            login_clicked = False
            for selector in login_selectors:
                try:
                    if await self.page.is_visible(selector):
                        await self.page.click(selector)
                        logger.info(f"Login clicked with: {selector}")
                        login_clicked = True
                        break
                except:
                    continue
            if not login_clicked:
                try:
                    await self.page.evaluate("""() => {
                        const form = document.querySelector("form");
                        if (form) form.submit();
                    }""")
                    logger.info("Form submitted via JavaScript")
                    login_clicked = True
                except:
                    pass
            if not login_clicked:
                try:
                    password_selector = f"input[name='{password_field_name}']"
                    await self.page.click(password_selector)
                    await self.page.keyboard.press('Enter')
                    logger.info("Enter key pressed in password field")
                    login_clicked = True
                except:
                    pass
            if not login_clicked:
                try:
                    await self.page.click('body')
                    await self.page.keyboard.press('Enter')
                    logger.info("Enter key pressed on body")
                    login_clicked = True
                except:
                    pass
            if not login_clicked:
                logger.error("All login submission methods failed")
                return False
            
            await self.smart_delay_async()
            await asyncio.sleep(8)
            
            await self.page.goto("https://adsha.re/surf", wait_until='networkidle', timeout=60000)
            await self.smart_delay_async()
            
            final_url = self.page.url.lower()
            logger.info(f"Final URL: {final_url}")
            
            if "surf" in final_url or "dashboard" in final_url:
                logger.info("🎉 LOGIN SUCCESSFUL!")
                self.state['is_logged_in'] = True
                self.state['last_activity'] = datetime.now()
                await self.send_telegram("✅ <b>ULTIMATE LOGIN SUCCESSFUL!</b>")
                return True
            elif "login" in final_url:
                logger.error("❌ LOGIN FAILED - Still on login page")
                return False
            else:
                logger.warning("⚠️ On unexpected page, but might be logged in")
                self.state['is_logged_in'] = True
                self.state['last_activity'] = datetime.now()
                return True
        except Exception as e:
            logger.error(f"❌ ULTIMATE LOGIN ERROR: {e}")
            return False

    async def take_screenshot(self):
        """Take screenshot and return file path"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_file = f"screenshot_{timestamp}.png"
            
            await self.page.screenshot(path=screenshot_file, full_page=True)
            logger.info(f"📸 Screenshot taken: {screenshot_file}")
            return screenshot_file
        except Exception as e:
            logger.error(f"❌ Screenshot failed: {e}")
            return None

    async def send_telegram(self, message):
        """Send telegram message"""
        send_telegram_message(message)

    async def ensure_logged_in(self):
        """Ensure we are logged in, perform login if needed"""
        if self.state['is_logged_in']:
            # Verify we're still logged in
            try:
                await self.page.goto(CONFIG['browser_url'], wait_until='networkidle', timeout=30000)
                page_state = await self.detect_page_state()
                if page_state != "LOGIN_REQUIRED":
                    return True
                else:
                    logger.warning("Session expired, re-login required")
                    self.state['is_logged_in'] = False
            except:
                self.state['is_logged_in'] = False
        
        # Perform login
        logger.info("🔐 Login required, attempting automatic login...")
        success = await self.force_login()
        if success:
            self.state['last_activity'] = datetime.now()
        return success
    
    async def close(self):
        """Close the browser"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
        finally:
            self.state['browser_active'] = False
            self.state['is_logged_in'] = False

# ==================== STATE MANAGEMENT ====================

class MonitorState:
    def __init__(self):
        self.is_running = False
        self.browser_active = False
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
        self.playwright_browser = PlaywrightBrowser()

state = MonitorState()

# ==================== LEADERBOARD PARSING ====================

class LeaderboardParser:
    @staticmethod
    def parse_with_beautifulsoup(html: str) -> List[Dict]:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            leaderboard = []
            
            # Multiple selector strategies
            selectors = [
                'div[style*="width:250px"][style*="margin:5px auto"]',
                'div[style*="width:250px"]',
                'div[style*="margin:5px auto"]',
                'div'
            ]
            
            entries = []
            for selector in selectors:
                entries = soup.select(selector)
                if entries:
                    logger.debug(f"Found {len(entries)} entries with selector: {selector}")
                    break
            
            if not entries:
                all_divs = soup.find_all('div')
                entries = [div for div in all_divs if 'T:' in div.get_text() and 'Y:' in div.get_text()]
                logger.debug(f"Found {len(entries)} entries with T: and Y: pattern")
            
            rank = 1
            for entry in entries:
                text = entry.get_text(strip=True)
                
                user_match = re.search(r'#(\d+)', text)
                if not user_match:
                    continue
                
                user_id = user_match.group(1)
                
                # Extract credits with multiple patterns
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
            
            logger.info(f"Parsed {len(leaderboard)} leaderboard entries")
            return leaderboard
        except Exception as e:
            logger.error(f"BeautifulSoup parsing error: {e}")
            return []

def fetch_leaderboard() -> Optional[List[Dict]]:
    """Fetch leaderboard with exact headers and cookies"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://adsha.re',
            'Connection': 'keep-alive',
            'Referer': 'https://adsha.re/affiliates',
            'Cookie': CONFIG['cookies'],
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        logger.debug("Fetching leaderboard with custom headers...")
        
        response = requests.post(
            CONFIG['leaderboard_url'],
            headers=headers,
            timeout=30,
            verify=True
        )
        
        logger.debug(f"Leaderboard response status: {response.status_code}")
        
        if response.status_code == 200:
            leaderboard = LeaderboardParser.parse_with_beautifulsoup(response.text)
            if leaderboard:
                logger.info(f"Successfully fetched leaderboard with {len(leaderboard)} entries")
                return leaderboard
            else:
                logger.warning("Leaderboard parsed but empty")
        else:
            logger.error(f"Leaderboard fetch failed with status: {response.status_code}")
            
        return None
            
    except Exception as e:
        logger.error(f"Network error fetching leaderboard: {e}")
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
        second_combined = second_place['today_credits'] + second_place['yesterday_credits']
        target = second_combined + state.safety_margin
        explanation = f"2nd combined ({second_combined}) + {state.safety_margin}"
    
    return target, explanation

def get_my_value(my_data: Dict) -> int:
    if state.strategy == 'today_only':
        return my_data['today_credits']
    else:
        return my_data['today_credits'] + my_data['yesterday_credits']

async def start_browser():
    """Start Firefox browser with Playwright"""
    if state.playwright_browser.state['browser_active']:
        return True
    
    try:
        logger.info("🚀 Starting Firefox browser with Playwright...")
        
        if await state.playwright_browser.setup_playwright():
            # Ensure login
            if await state.playwright_browser.ensure_logged_in():
                logger.info("✅ Firefox browser started and logged in")
                return True
            else:
                logger.error("❌ Firefox started but login failed")
                return False
        else:
            logger.error("❌ Firefox setup failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Browser start error: {e}")
        return False

async def stop_browser():
    """Stop Firefox browser"""
    logger.info("🛑 Stopping Firefox browser...")
    await state.playwright_browser.close()
    logger.info("✅ Firefox browser stopped")

# ==================== TELEGRAM FUNCTIONS ====================

def send_telegram_message(message: str):
    if not CONFIG.get('chat_id'):
        return
    
    try:
        url = f"https://api.telegram.org/bot{CONFIG['telegram_token']}/sendMessage"
        data = {
            'chat_id': CONFIG['chat_id'], 
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=data, timeout=15)
        if response.status_code != 200:
            logger.error(f"Telegram message failed: {response.text}")
    except Exception as e:
        logger.error(f"Telegram message failed: {e}")

def send_telegram_photo(photo_path: str, caption: str = ""):
    """Send photo via Telegram"""
    if not CONFIG.get('chat_id'):
        return
    
    try:
        url = f"https://api.telegram.org/bot{CONFIG['telegram_token']}/sendPhoto"
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': CONFIG['chat_id'], 'caption': caption}
            response = requests.post(url, files=files, data=data, timeout=30)
            
        # Clean up screenshot file
        if os.path.exists(photo_path):
            os.remove(photo_path)
            
        if response.status_code == 200:
            logger.info("✅ Screenshot sent successfully")
        else:
            logger.error(f"❌ Telegram photo failed: {response.text}")
        
    except Exception as e:
        logger.error(f"❌ Telegram photo failed: {e}")

def format_leaderboard_message(leaderboard: List[Dict]) -> str:
    """Format leaderboard for Telegram"""
    if not leaderboard:
        return "❌ No leaderboard data available"
    
    message = "🏆 <b>LEADERBOARD</b>\n\n"
    message += "<code>"
    message += "Rank  User    Today   Yesterday  DB\n"
    message += "------------------------------------\n"
    
    for entry in leaderboard[:8]:  # Top 8
        rank = entry['rank']
        user_id = entry['user_id']
        today = entry['today_credits']
        yesterday = entry['yesterday_credits']
        day_before = entry['day_before_credits']
        
        if user_id == CONFIG['my_user_id']:
            marker = "➤ "
        elif rank == 1:
            marker = "🥇"
        elif rank == 2:
            marker = "🥈" 
        elif rank == 3:
            marker = "🥉"
        else:
            marker = "  "
        
        message += f"{marker}{rank:<2} #{user_id:<6} {today:<7} {yesterday:<10} {day_before:<5}\n"
    
    message += "</code>"
    return message

def format_status_message() -> str:
    """Format status message for Telegram"""
    if not state.leaderboard:
        return "❌ No competition data available"
    
    my_data = None
    for entry in state.leaderboard:
        if entry['user_id'] == CONFIG['my_user_id']:
            my_data = entry
            break
    
    if not my_data:
        return f"❌ User #{CONFIG['my_user_id']} not in top 10"
    
    my_value = get_my_value(my_data)
    message = f"🎯 <b>COMPETITION STATUS</b>\n\n"
    message += f"📊 <b>Position:</b> #{state.my_position}\n"
    message += f"💎 <b>My Credits Today:</b> {my_value}\n"
    
    if state.my_position == 1:
        target, explanation = calculate_target(state.leaderboard)
        message += f"🎯 <b>Target:</b> {target} ({explanation})\n"
        
        if my_value >= target:
            message += "✅ <b>TARGET ACHIEVED!</b>\n"
            message += f"📈 <b>Lead:</b> +{my_value - target}\n"
        else:
            gap = target - my_value
            message += "🏃 <b>CHASING TARGET</b>\n"
            message += f"📈 <b>Need:</b> {gap} more credits\n"
            
            if state.credits_growth_rate > 0 and gap > 0:
                hours_needed = gap / state.credits_growth_rate
                message += f"⏱️ <b>ETA:</b> {hours_needed:.1f} hours\n"
    
    else:
        first_place = state.leaderboard[0]
        gap = first_place['today_credits'] - my_data['today_credits']
        message += f"🥇 <b>Leader:</b> #{first_place['user_id']}\n"
        message += f"📉 <b>Gap:</b> {gap} credits\n"
    
    # Add browser status
    browser_status = "✅ Active" if state.playwright_browser.state['browser_active'] else "❌ Inactive"
    login_status = "✅ Logged In" if state.playwright_browser.state['is_logged_in'] else "❌ Not Logged In"
    
    message += f"\n🖥️ <b>Browser:</b> {browser_status}\n"
    message += f"🔐 <b>Login:</b> {login_status}\n"
    
    if state.last_check_time:
        last_checked = state.last_check_time.strftime('%H:%M:%S')
        message += f"🕒 <b>Last Checked:</b> {last_checked}\n"
    
    return message

async def handle_telegram_command(command: str, chat_id: int):
    """Handle Telegram bot commands"""
    CONFIG['chat_id'] = chat_id
    
    if command == '/start':
        state.is_running = True
        send_telegram_message("✅ <b>Monitor STARTED!</b>")
        await check_competition_status()
        
    elif command == '/stop':
        state.is_running = False
        await stop_browser()
        send_telegram_message("⏹️ <b>Monitor STOPPED!</b>")
        
    elif command == '/status':
        await check_competition_status()
        status_msg = format_status_message()
        send_telegram_message(status_msg)
        
    elif command == '/leaderboard':
        leaderboard = fetch_leaderboard()
        if leaderboard:
            leaderboard_msg = format_leaderboard_message(leaderboard)
            send_telegram_message(leaderboard_msg)
        else:
            send_telegram_message("❌ <b>Failed to fetch leaderboard</b>")
            
    elif command == '/screenshot':
        if state.playwright_browser.state['browser_active']:
            screenshot_file = await state.playwright_browser.take_screenshot()
            if screenshot_file:
                send_telegram_photo(screenshot_file, "📸 <b>Current Browser State</b>")
            else:
                send_telegram_message("❌ <b>Failed to take screenshot</b>")
        else:
            send_telegram_message("❌ <b>Browser is not active</b>")
            
    elif command == '/restart_browser':
        await stop_browser()
        await asyncio.sleep(2)
        if await start_browser():
            send_telegram_message("🔁 <b>Browser restarted successfully!</b>")
        else:
            send_telegram_message("❌ <b>Browser restart failed!</b>")
            
    elif command == '/debug':
        debug_info = f"🔧 <b>DEBUG INFO</b>\n\n"
        debug_info += f"🖥️ Browser Active: {state.playwright_browser.state['browser_active']}\n"
        debug_info += f"🔐 Logged In: {state.playwright_browser.state['is_logged_in']}\n"
        debug_info += f"🎯 Monitor Running: {state.is_running}\n"
        debug_info += f"📊 Leaderboard Entries: {len(state.leaderboard) if state.leaderboard else 0}\n"
        debug_info += f"👤 My Position: {state.my_position}\n"
        
        send_telegram_message(debug_info)

# ==================== TELEGRAM BOT ====================

async def telegram_bot_loop():
    last_update_id = 0
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{CONFIG['telegram_token']}/getUpdates?timeout=30&offset={last_update_id + 1}"
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
                                await handle_telegram_command(command, chat_id)
        except Exception as e:
            logger.error(f"Telegram bot error: {e}")
        
        await asyncio.sleep(10)

# ==================== COMPETITION CHECK ====================

async def check_competition_status():
    """Single competition check"""
    
    current_time = datetime.now()
    state.last_check_time = current_time
    
    leaderboard = fetch_leaderboard()
    if not leaderboard:
        logger.error("Failed to fetch leaderboard")
        await start_browser()
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
        await start_browser()
        return
    
    my_value = get_my_value(my_data)
    
    # PREDICTION CALCULATION
    if state.last_my_credits > 0 and state.last_credits_time:
        time_diff_hours = (current_time - state.last_credits_time).total_seconds() / 3600.0
        credits_gained = my_value - state.last_my_credits
        
        if credits_gained > 0 and time_diff_hours > 0:
            state.credits_growth_rate = credits_gained / time_diff_hours
        else:
            state.credits_growth_rate = 0
    else:
        state.credits_growth_rate = 0
    
    # Update credits tracking
    state.last_my_credits = my_value
    state.last_credits_time = current_time
    
    # Competition logic
    if state.my_position != 1:
        if not state.playwright_browser.state['browser_active']:
            await start_browser()
        state.target_achieved = False
    else:
        target, explanation = calculate_target(state.leaderboard)
        state.current_target = target
        
        if my_value >= target:
            if state.playwright_browser.state['browser_active']:
                await stop_browser()
            state.target_achieved = True
        else:
            if not state.playwright_browser.state['browser_active']:
                await start_browser()
            state.target_achieved = False
    
    # Log status
    logger.info(f"Position: #{state.my_position}, Credits: {my_value}, Growth Rate: {state.credits_growth_rate:.1f}/hour")

# ==================== MAIN LOOP ====================

async def main_loop():
    logger.info("AdShare Monitor v8.0 - Railway Edition STARTED")
    logger.info("Using Playwright Firefox with ZIP profile loading")
    
    send_telegram_message("🚀 <b>AdShare Monitor v8.0 Started!</b>\nPlaywright Firefox Edition on Railway")
    
    if CONFIG['auto_start']:
        state.is_running = True
        await check_competition_status()
    
    last_check = datetime.now()
    
    while True:
        try:
            if state.is_running:
                current_time = datetime.now()
                if (current_time - last_check).total_seconds() >= CONFIG['leaderboard_check_interval']:
                    await check_competition_status()
                    last_check = current_time
                
                await asyncio.sleep(10)
            else:
                await asyncio.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await stop_browser()
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            await asyncio.sleep(30)

def signal_handler(sig, frame):
    logger.info("Shutdown signal received")
    asyncio.create_task(stop_browser())
    sys.exit(0)

async def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start telegram bot in background
    bot_task = asyncio.create_task(telegram_bot_loop())
    
    # Start main loop
    await main_loop()
    
    # Cancel bot task when main loop ends
    bot_task.cancel()

if __name__ == '__main__':
    asyncio.run(main())
