#!/usr/bin/env python3
"""
AdShare Monitor v7.2 - Railway Fixed Edition
Enhanced profile handling with Firefox 144.0
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
    
    # Profile Settings
    'firefox_profile_url': "https://github.com/huijuo14/playright-/releases/download/v1/firefox_profile_backup.tar.gz",
    'profile_name': "o9clx99u.surf",
    
    # Technical Settings
    'leaderboard_url': 'https://adsha.re/ten',
    'timezone': 'Asia/Kolkata',
    
    # Headers for leaderboard (EXACT CURL HEADERS)
    'leaderboard_headers': {
        'authority': 'adsha.re',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'cookie': 'adshare_e=bonna.b.o.rre.z%40gmail.com; adshare_s=e4dc9d210bb38a86cd360253a82feb2cc6ed84f5ddf778be89484fb476998e0dfc31280c575a38a2467067cd6ec1d6ff7e25aa46dedd6ea454831df26365dfc2; adshare_d=20251025; adshare_h=https%3A%2F%2Fadsha.re%2Faffiliates',
        'origin': 'https://adsha.re',
        'pragma': 'no-cache',
        'referer': 'https://adsha.re/affiliates',
        'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    },
    
    # Auto Start
    'auto_start': True,
}

# ==================== ENHANCED LOGGING ====================

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
        self.target_profile_name = "o9clx99u.surf"
        
    def cleanup_old_profiles(self):
        """Remove old profiles to avoid conflicts"""
        try:
            logger.info("PROFILE: Cleaning up old profiles...")
            for item in self.profile_path.iterdir():
                if item.is_dir() and "surf" in item.name.lower():
                    if self.target_profile_name not in item.name:
                        logger.info(f"PROFILE: Removing old profile {item.name}")
                        shutil.rmtree(item, ignore_errors=True)
        except Exception as e:
            logger.error(f"PROFILE CLEANUP ERROR: {e}")
    
    def download_and_extract_profile(self):
        """Download and extract Firefox profile with enhanced error handling"""
        try:
            backup_url = CONFIG['firefox_profile_url']
            backup_file = "firefox_profile_backup.tar.gz"
            
            logger.info(f"DOWNLOAD: Starting download from {backup_url}")
            
            # Ensure firefox directory exists
            self.profile_path.mkdir(parents=True, exist_ok=True)
            
            # Download with progress
            def report_progress(block_num, block_size, total_size):
                percent = int(block_num * block_size * 100 / total_size)
                if percent % 20 == 0:
                    logger.info(f"DOWNLOAD: {percent}% complete")
            
            urllib.request.urlretrieve(backup_url, backup_file, report_progress)
            
            if not os.path.exists(backup_file):
                logger.error("DOWNLOAD: Failed to download profile backup")
                return False
            
            file_size = os.path.getsize(backup_file)
            logger.info(f"DOWNLOAD: Success - {file_size} bytes downloaded")
            
            # Clean up old profiles first
            self.cleanup_old_profiles()
            
            # Extract with detailed logging
            logger.info("EXTRACT: Starting extraction...")
            with tarfile.open(backup_file, 'r:gz') as tar:
                members = tar.getmembers()
                logger.info(f"EXTRACT: Archive contains {len(members)} items")
                
                # Extract with preservation
                tar.extractall(self.profile_path)
                
                # Log extracted files
                extracted_dirs = []
                for member in members[:10]:  # Log first 10 files
                    if member.isdir():
                        extracted_dirs.append(member.name)
                
                logger.info(f"EXTRACT: Sample directories: {extracted_dirs[:5]}")
            
            # Clean up backup file
            os.remove(backup_file)
            logger.info("EXTRACT: Cleanup completed")
            
            return True
            
        except Exception as e:
            logger.error(f"PROFILE SETUP FAILED: {e}")
            return False
    
    def verify_profile_compatibility(self, profile_dir):
        """Verify profile compatibility with Firefox 144.0"""
        try:
            compatibility_file = Path(profile_dir) / "compatibility.ini"
            if compatibility_file.exists():
                content = compatibility_file.read_text()
                logger.info(f"PROFILE COMPATIBILITY: {compatibility_file}")
            return True
        except Exception as e:
            logger.warning(f"PROFILE COMPATIBILITY CHECK FAILED: {e}")
            return True  # Continue anyway
    
    def get_profile_directory(self):
        """Get the profile directory with enhanced debugging"""
        try:
            logger.info("PROFILE SEARCH: Looking for profile directory...")
            
            # List all directories for debugging
            dirs_before = list(self.profile_path.iterdir())
            logger.info(f"PROFILE DIRS BEFORE: {[d.name for d in dirs_before if d.is_dir()]}")
            
            # Look for our specific profile
            for item in self.profile_path.iterdir():
                if item.is_dir() and self.target_profile_name in item.name:
                    logger.info(f"PROFILE FOUND: {item}")
                    
                    # Verify compatibility
                    self.verify_profile_compatibility(item)
                    
                    # Check if profile is complete
                    required_files = ['prefs.js', 'places.sqlite', 'cookies.sqlite']
                    missing_files = []
                    for file in required_files:
                        if not (item / file).exists():
                            missing_files.append(file)
                    
                    if missing_files:
                        logger.warning(f"PROFILE MISSING FILES: {missing_files}")
                    else:
                        logger.info("PROFILE: All required files present")
                    
                    return str(item)
            
            # If not found, download it
            logger.info("PROFILE NOT FOUND: Attempting download...")
            if self.download_and_extract_profile():
                # Try to find it again after download
                for item in self.profile_path.iterdir():
                    if item.is_dir() and self.target_profile_name in item.name:
                        logger.info(f"PROFILE FOUND AFTER DOWNLOAD: {item}")
                        return str(item)
            
            logger.error("PROFILE: Could not find or download profile directory")
            return None
            
        except Exception as e:
            logger.error(f"PROFILE SEARCH FAILED: {e}")
            return None

# ==================== PLAYWRIGHT BROWSER MANAGER ====================

class PlaywrightBrowser:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.state = {
            'is_logged_in': False,
            'browser_active': False,
            'last_activity': None
        }
        self.profile_manager = FirefoxProfileManager()
        
    async def setup_playwright(self):
        """Setup Playwright with Firefox 144.0 and profile"""
        try:
            logger.info("PLAYWRIGHT: Starting setup...")
            
            # Check if browsers are installed
            try:
                from playwright import install
                logger.info("PLAYWRIGHT: Installing browsers if needed...")
                install()
            except Exception as e:
                logger.info(f"PLAYWRIGHT: Browser install check: {e}")
            
            self.playwright = await async_playwright().start()
            logger.info("PLAYWRIGHT: Engine started")
            
            # Get Firefox profile directory
            profile_dir = self.profile_manager.get_profile_directory()
            
            if not profile_dir:
                logger.error("PLAYWRIGHT: No profile directory found")
                return False
            
            logger.info(f"PLAYWRIGHT: Using profile - {profile_dir}")
            
            # Launch Firefox with specific executable path for Firefox 144.0
            firefox_executable_path = "/opt/firefox/firefox"
            
            logger.info("PLAYWRIGHT: Launching Firefox with args...")
            self.browser = await self.playwright.firefox.launch(
                headless=CONFIG['headless_mode'],
                executable_path=firefox_executable_path,
                args=[
                    f"--window-size={CONFIG['browser_width']},{CONFIG['browser_height']}",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor"
                ],
                firefox_user_prefs={
                    "dom.webdriver.enabled": False,
                    "useAutomationExtension": False,
                    "browser.startup.homepage": "about:blank",
                    "browser.startup.page": 0
                }
            )
            
            # Create context
            context = await self.browser.new_context(
                viewport={'width': CONFIG['browser_width'], 'height': CONFIG['browser_height']},
                user_agent=CONFIG['leaderboard_headers']['user-agent'],
                ignore_https_errors=True
            )
            
            self.page = await context.new_page()
            
            # Enhanced stealth
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """)
            
            self.state['browser_active'] = True
            self.state['last_activity'] = datetime.now()
            logger.info("PLAYWRIGHT: Firefox started successfully")
            return True
            
        except Exception as e:
            logger.error(f"PLAYWRIGHT SETUP FAILED: {e}")
            return False
    
    async def smart_delay_async(self, min_delay=2, max_delay=5):
        """Random delay between actions"""
        import random
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    async def detect_page_state(self):
        """Detect current page state"""
        try:
            current_url = self.page.url.lower()
            page_content = await self.page.content()
            
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
                return f"UNKNOWN: {current_url}"
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    async def force_login(self):
        """EXACT WORKING LOGIN FUNCTION - Playwright Version"""
        try:
            logger.info("LOGIN: Starting ultimate login...")
            await self.page.goto("https://adsha.re/login", wait_until='networkidle', timeout=90000)
            await self.page.wait_for_selector("body", timeout=30000)
            await self.smart_delay_async()
            
            page_content = await self.page.content()
            soup = BeautifulSoup(page_content, 'html.parser')
            all_forms = soup.find_all('form')
            logger.info(f"LOGIN: Found {len(all_forms)} forms")
            
            form = soup.find('form', {'name': 'login'})
            if not form:
                logger.warning("LOGIN: No login form found by name, trying first form")
                form = all_forms[0] if all_forms else None
            if not form:
                logger.error("LOGIN: No forms found at all!")
                return False
            
            password_field_name = None
            for field in form.find_all('input'):
                field_name = field.get('name', '')
                field_value = field.get('value', '')
                if field_value == 'Password' and field_name != 'mail' and field_name:
                    password_field_name = field_name
                    logger.info(f"LOGIN: Found password field by value: {password_field_name}")
                    break
            if not password_field_name:
                password_fields = form.find_all('input', {'type': 'password'})
                if password_fields:
                    password_field_name = password_fields[0].get('name')
                    logger.info(f"LOGIN: Found password field by type: {password_field_name}")
            if not password_field_name:
                for field in form.find_all('input'):
                    field_name = field.get('name', '')
                    field_type = field.get('type', '')
                    if field_name and field_name != 'mail' and field_type != 'email':
                        password_field_name = field_name
                        logger.info(f"LOGIN: Found password field by exclusion: {password_field_name}")
                        break
            if not password_field_name:
                inputs = form.find_all('input')
                if len(inputs) >= 2:
                    password_field_name = inputs[1].get('name')
                    logger.info(f"LOGIN: Found password field by position: {password_field_name}")
            if not password_field_name:
                logger.error("LOGIN: Could not find password field by any method")
                return False
            
            logger.info("LOGIN: Filling email...")
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
                        logger.info(f"LOGIN: Email filled with: {selector}")
                        email_filled = True
                        break
                except:
                    continue
            if not email_filled:
                logger.error("LOGIN: All email filling methods failed")
                return False
            
            await self.smart_delay_async()
            
            logger.info("LOGIN: Filling password...")
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
                        logger.info(f"LOGIN: Password filled with: {selector}")
                        password_filled = True
                        break
                except:
                    continue
            if not password_filled:
                logger.error("LOGIN: All password filling methods failed")
                return False
            
            await self.smart_delay_async()
            
            logger.info("LOGIN: Submitting form...")
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
                        logger.info(f"LOGIN: Login clicked with: {selector}")
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
                    logger.info("LOGIN: Form submitted via JavaScript")
                    login_clicked = True
                except:
                    pass
            if not login_clicked:
                try:
                    password_selector = f"input[name='{password_field_name}']"
                    await self.page.click(password_selector)
                    await self.page.keyboard.press('Enter')
                    logger.info("LOGIN: Enter key pressed in password field")
                    login_clicked = True
                except:
                    pass
            if not login_clicked:
                try:
                    await self.page.click('body')
                    await self.page.keyboard.press('Enter')
                    logger.info("LOGIN: Enter key pressed on body")
                    login_clicked = True
                except:
                    pass
            if not login_clicked:
                logger.error("LOGIN: All login submission methods failed")
                return False
            
            await self.smart_delay_async()
            await asyncio.sleep(8)
            
            await self.page.goto("https://adsha.re/surf", wait_until='networkidle', timeout=90000)
            await self.smart_delay_async()
            
            final_url = self.page.url.lower()
            logger.info(f"LOGIN: Final URL: {final_url}")
            
            if "surf" in final_url or "dashboard" in final_url:
                logger.info("LOGIN: SUCCESSFUL!")
                self.state['is_logged_in'] = True
                await self.send_telegram("✅ <b>LOGIN SUCCESSFUL!</b>")
                return True
            elif "login" in final_url:
                logger.error("LOGIN: FAILED - Still on login page")
                return False
            else:
                logger.warning(f"LOGIN: On unexpected page: {final_url}")
                self.state['is_logged_in'] = True
                return True
        except Exception as e:
            logger.error(f"LOGIN ERROR: {e}")
            return False

    async def take_screenshot(self):
        """Take screenshot and return file path"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_file = f"screenshot_{timestamp}.png"
            
            await self.page.screenshot(path=screenshot_file, full_page=True)
            logger.info(f"SCREENSHOT: Taken - {screenshot_file}")
            return screenshot_file
        except Exception as e:
            logger.error(f"SCREENSHOT FAILED: {e}")
            return None

    async def send_telegram(self, message):
        """Send telegram message"""
        send_telegram_message(message)

    async def ensure_logged_in(self):
        """Ensure we are logged in, perform login if needed"""
        if self.state['is_logged_in']:
            return True
            
        try:
            await self.page.goto(CONFIG['browser_url'], wait_until='networkidle', timeout=60000)
            await self.smart_delay_async()
            
            page_state = await self.detect_page_state()
            logger.info(f"LOGIN CHECK: Page state - {page_state}")
            
            if page_state == "LOGIN_REQUIRED":
                logger.info("LOGIN: Required, attempting automatic login...")
                return await self.force_login()
            elif page_state in ["GAME_ACTIVE", "GAME_READY", "GAME_LOADING"]:
                self.state['is_logged_in'] = True
                logger.info("LOGIN: Already logged in")
                return True
            else:
                logger.warning(f"LOGIN: Unexpected page state: {page_state}")
                return await self.force_login()
        except Exception as e:
            logger.error(f"LOGIN CHECK ERROR: {e}")
            return await self.force_login()
    
    async def close(self):
        """Close the browser"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.state['browser_active'] = False
            self.state['is_logged_in'] = False
            logger.info("BROWSER: Closed successfully")
        except Exception as e:
            logger.error(f"BROWSER CLOSE ERROR: {e}")

# ==================== STATE MANAGEMENT ====================

class MonitorState:
    def __init__(self):
        self.is_running = False
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
                'div.leaderboard-entry',
                'div.entry'
            ]
            
            entries = []
            for selector in selectors:
                entries = soup.select(selector)
                if entries:
                    logger.info(f"LEADERBOARD: Found entries with selector: {selector}")
                    break
            
            # Fallback: find by text content
            if not entries:
                all_divs = soup.find_all('div')
                entries = [div for div in all_divs if 'T:' in div.get_text() and 'Y:' in div.get_text()]
                logger.info(f"LEADERBOARD: Found {len(entries)} entries by text content")
            
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
            
            logger.info(f"LEADERBOARD: Parsed {len(leaderboard)} entries")
            return leaderboard
        except Exception as e:
            logger.error(f"LEADERBOARD PARSING ERROR: {e}")
            return []
    
    @staticmethod
    def parse(html: str) -> List[Dict]:
        leaderboard = LeaderboardParser.parse_with_beautifulsoup(html)
        leaderboard.sort(key=lambda x: x['rank'])
        return leaderboard

def fetch_leaderboard() -> Optional[List[Dict]]:
    try:
        logger.info("LEADERBOARD: Fetching...")
        
        # Use exact curl headers
        headers = CONFIG['leaderboard_headers']
        
        response = requests.post(
            CONFIG['leaderboard_url'],
            headers=headers,
            timeout=30,
            verify=True
        )
        
        if response.status_code == 200:
            leaderboard = LeaderboardParser.parse(response.text)
            if leaderboard:
                logger.info(f"LEADERBOARD: Success - {len(leaderboard)} entries")
                return leaderboard
            else:
                logger.error("LEADERBOARD: No entries parsed")
        else:
            logger.error(f"LEADERBOARD: HTTP {response.status_code}")
        
        return None
            
    except Exception as e:
        logger.error(f"LEADERBOARD ERROR: {e}")
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

def format_leaderboard_for_telegram(leaderboard: List[Dict]) -> str:
    """Format leaderboard for Telegram message"""
    if not leaderboard:
        return "No leaderboard data available"
    
    message = "🏆 <b>LEADERBOARD</b>\n\n"
    message += "<code>Rank User     Today   Yesterday DB</code>\n"
    message += "<code>-----------------------------------</code>\n"
    
    for entry in leaderboard[:8]:  # Top 8
        rank = entry['rank']
        user_id = entry['user_id']
        today = entry['today_credits']
        yesterday = entry['yesterday_credits']
        day_before = entry['day_before_credits']
        
        if user_id == CONFIG['my_user_id']:
            marker = "➤"
        elif rank == 1:
            marker = "🥇"
        elif rank == 2:
            marker = "🥈"
        elif rank == 3:
            marker = "🥉"
        else:
            marker = "  "
        
        message += f"<code>{marker} {rank:<2} #{user_id:<6} {today:<7} {yesterday:<9} {day_before}</code>\n"
    
    return message

def format_status_for_telegram() -> str:
    """Format competition status for Telegram"""
    if not state.leaderboard or not state.my_position:
        return "No competition data available"
    
    my_data = None
    for entry in state.leaderboard:
        if entry['user_id'] == CONFIG['my_user_id']:
            my_data = entry
            break
    
    if not my_data:
        return "User not found in leaderboard"
    
    my_value = get_my_value(my_data)
    
    message = "🎯 <b>COMPETITION STATUS</b>\n\n"
    message += f"📊 <b>Position:</b> #{state.my_position}\n"
    message += f"💰 <b>My Credits Today:</b> {my_value}\n"
    
    if state.my_position == 1:
        target, explanation = calculate_target(state.leaderboard)
        message += f"🎯 <b>Target:</b> {target} ({explanation})\n"
        
        if my_value >= target:
            message += "✅ <b>TARGET ACHIEVED!</b>\n"
            message += f"📈 <b>Lead:</b> +{my_value - target}\n"
        else:
            gap = target - my_value
            message += "🏃 <b>CHASING TARGET</b>\n"
            message += f"📋 <b>Need:</b> {gap} more credits\n"
            
            if state.credits_growth_rate > 0 and gap > 0:
                hours_needed = gap / state.credits_growth_rate
                completion_time = datetime.now() + timedelta(hours=hours_needed)
                message += f"⏱️ <b>ETA:</b> {hours_needed:.1f} hours\n"
                message += f"🕒 <b>Completion:</b> {completion_time.strftime('%H:%M')}\n"
    else:
        first_place = state.leaderboard[0]
        gap = first_place['today_credits'] - my_data['today_credits']
        message += f"⚠️ <b>NOT #1</b> - Currently #{state.my_position}\n"
        message += f"🥇 <b>Leader:</b> #{first_place['user_id']}\n"
        message += f"📉 <b>Gap:</b> {gap} credits\n"
    
    if state.last_check_time:
        message += f"\n🕒 <b>Last Checked:</b> {state.last_check_time.strftime('%H:%M:%S')}"
    
    return message

# ==================== BROWSER MANAGEMENT ====================

async def start_browser():
    """Start Firefox browser with Playwright"""
    if state.playwright_browser.state['browser_active']:
        return True
    
    try:
        logger.info("BROWSER: Starting...")
        
        if await state.playwright_browser.setup_playwright():
            # Ensure login
            if await state.playwright_browser.ensure_logged_in():
                logger.info("BROWSER: Started and logged in successfully")
                return True
            else:
                logger.error("BROWSER: Started but login failed")
                return False
        else:
            logger.error("BROWSER: Setup failed")
            return False
            
    except Exception as e:
        logger.error(f"BROWSER START ERROR: {e}")
        return False

async def stop_browser():
    """Stop Firefox browser"""
    logger.info("BROWSER: Stopping...")
    await state.playwright_browser.close()
    logger.info("BROWSER: Stopped")

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
        if response.status_code == 200:
            logger.info("TELEGRAM: Message sent successfully")
        else:
            logger.error(f"TELEGRAM: Failed to send message - {response.status_code}")
    except Exception as e:
        logger.error(f"TELEGRAM MESSAGE FAILED: {e}")

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
            logger.info("TELEGRAM: Photo sent successfully")
        else:
            logger.error(f"TELEGRAM: Failed to send photo - {response.status_code}")
        
    except Exception as e:
        logger.error(f"TELEGRAM PHOTO FAILED: {e}")

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
        
    elif command == '/leaderboard':
        if state.leaderboard:
            message = format_leaderboard_for_telegram(state.leaderboard)
            send_telegram_message(message)
        else:
            send_telegram_message("❌ <b>No leaderboard data available</b>")
        
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
            
    elif command == '/login_status':
        if state.playwright_browser.state['is_logged_in']:
            send_telegram_message("✅ <b>Logged IN</b>")
        else:
            send_telegram_message("❌ <b>Not logged in</b>")
            
    elif command == '/debug':
        debug_info = f"""
🔧 <b>DEBUG INFO</b>

🏃 <b>Monitor Running:</b> {state.is_running}
🌐 <b>Browser Active:</b> {state.playwright_browser.state['browser_active']}
🔐 <b>Logged In:</b> {state.playwright_browser.state['is_logged_in']}
📊 <b>Leaderboard Entries:</b> {len(state.leaderboard)}
🎯 <b>My Position:</b> {state.my_position}
📈 <b>Growth Rate:</b> {state.credits_growth_rate:.1f}/hour
        """
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
            logger.error(f"TELEGRAM BOT ERROR: {e}")
        
        await asyncio.sleep(10)

# ==================== COMPETITION CHECK ====================

async def check_competition_status():
    """Single competition check"""
    
    current_time = datetime.now()
    state.last_check_time = current_time
    
    logger.info("COMPETITION: Checking status...")
    
    leaderboard = fetch_leaderboard()
    if not leaderboard:
        logger.error("COMPETITION: Failed to fetch leaderboard")
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
        logger.error(f"COMPETITION: User #{CONFIG['my_user_id']} not in top 10!")
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
    
    # Send status to Telegram
    status_message = format_status_for_telegram()
    send_telegram_message(status_message)
    
    logger.info(f"COMPETITION: Check completed - Position #{state.my_position}")

# ==================== MAIN LOOP ====================

async def main_loop():
    logger.info("🚀 AdShare Monitor v7.2 - Railway Edition STARTED")
    logger.info("Using Playwright Firefox with enhanced profile management")
    
    send_telegram_message("🚀 <b>AdShare Monitor v7.2 Started!</b>\nEnhanced Firefox 144.0 Edition")
    
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
            logger.error(f"MAIN LOOP ERROR: {e}")
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
