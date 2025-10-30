#!/usr/bin/env python3
"""
AdShare Monitor v7.0 - Playwright Edition for Railway & Colab
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

try:
    import requests
    from bs4 import BeautifulSoup
    import pytz
    from colorama import Fore, Back, Style, init
    from playwright.async_api import async_playwright
    import asyncio
except ImportError:
    print("Installing required packages...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "requests", "beautifulsoup4", "pytz", "colorama",
        "playwright", "urllib3", "asyncio"
    ], check=True)
    import requests
    from bs4 import BeautifulSoup
    import pytz
    from colorama import Fore, Back, Style, init
    from playwright.async_api import async_playwright
    import asyncio

# Install Playwright browsers
try:
    subprocess.run([sys.executable, "-m", "playwright", "install", "firefox"], check=True)
except:
    pass

# Initialize colorama
init(autoreset=True)

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
    'cookies': 'adshare_e=bonna.b.o.rre.z%40gmail.com; adshare_s=e4dc9d210bb38a86cd360253a82feb2cc6ed84f5ddf778be89484fb476998e0dfc31280c575a38a2467067cd6ec1d6ff7e25aa46dedd6ea454831df26365dfc2; adshare_d=20251025; adshare_h=https%3A%2F%2Fadsha.re%2Faffiliates',
    'timezone': 'Asia/Kolkata',
    
    # Auto Start
    'auto_start': True,
}

# ==================== ENHANCED LOGGING ====================

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE,
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
))

file_handler = logging.FileHandler('adshare_monitor.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# ==================== FIREFOX PROFILE MANAGEMENT ====================

class FirefoxProfileManager:
    def __init__(self):
        self.profile_path = Path.home() / '.mozilla' / 'firefox'
        self.target_profile_name = "o9clx99u.surf"
        
    def download_and_extract_profile(self):
        """Download and extract Firefox profile from GitHub releases"""
        try:
            backup_url = CONFIG['firefox_profile_url']
            backup_file = "firefox_profile_backup.tar.gz"
            
            logger.info(f"📥 Downloading Firefox profile from {backup_url}")
            
            # Download the profile backup
            urllib.request.urlretrieve(backup_url, backup_file)
            
            if not os.path.exists(backup_file):
                logger.error("❌ Failed to download profile backup")
                return False
            
            # Ensure firefox directory exists
            self.profile_path.mkdir(parents=True, exist_ok=True)
            
            # Extract the backup
            logger.info("📦 Extracting Firefox profile...")
            with tarfile.open(backup_file, 'r:gz') as tar:
                # Get the list of files to see what we're extracting
                members = tar.getmembers()
                logger.info(f"📁 Archive contains {len(members)} items")
                
                # Extract everything to firefox directory
                tar.extractall(self.profile_path)
            
            # Clean up
            os.remove(backup_file)
            
            logger.info("✅ Firefox profile extraction completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Profile setup failed: {e}")
            return False
    
    def get_profile_directory(self):
        """Find the profile directory"""
        try:
            # Method 1: Search directories for profile name
            for item in self.profile_path.iterdir():
                if item.is_dir() and self.target_profile_name in item.name:
                    logger.info(f"✅ Found profile via directory search: {item}")
                    return str(item)
            
            # Method 2: Search for any directory containing the pattern
            for item in self.profile_path.iterdir():
                if item.is_dir() and "o9clx99u" in item.name:
                    logger.info(f"✅ Found matching profile: {item}")
                    return str(item)
            
            # Method 3: Try to download if not found
            logger.info("🔄 Profile not found locally, downloading...")
            if self.download_and_extract_profile():
                # Search again after download
                for item in self.profile_path.iterdir():
                    if item.is_dir() and (self.target_profile_name in item.name or "o9clx99u" in item.name):
                        logger.info(f"✅ Found profile after download: {item}")
                        return str(item)
            
            logger.error("❌ No profile found after all attempts")
            return None
            
        except Exception as e:
            logger.error(f"❌ Profile search failed: {e}")
            return None

# ==================== PLAYWRIGHT BROWSER MANAGER ====================

class PlaywrightBrowser:
    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None
        self.state = {
            'is_logged_in': False,
            'browser_active': False
        }
        self.profile_manager = FirefoxProfileManager()
        
    async def setup_browser(self):
        """Setup Playwright Firefox with profile"""
        try:
            logger.info("🚀 Starting Firefox with Playwright...")
            
            # Get profile directory
            profile_dir = self.profile_manager.get_profile_directory()
            if not profile_dir:
                logger.error("❌ Profile directory not found")
                return False
            
            logger.info(f"📁 Using Firefox profile: {profile_dir}")
            
            playwright = await async_playwright().start()
            
            # Launch Firefox with profile
            self.browser = await playwright.firefox.launch(
                headless=CONFIG['headless_mode'],
                args=[
                    f"--window-size={CONFIG['browser_width']},{CONFIG['browser_height']}",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            
            # Create context with persistent storage
            self.context = await self.browser.new_context(
                viewport={'width': CONFIG['browser_width'], 'height': CONFIG['browser_height']},
                user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
                storage_state=profile_dir if os.path.exists(os.path.join(profile_dir, 'storage.json')) else None
            )
            
            self.page = await self.context.new_page()
            
            # Set extra HTTP headers
            await self.page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
            })
            
            self.state['browser_active'] = True
            logger.info("✅ Playwright Firefox started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Playwright setup failed: {e}")
            return False
    
    async def smart_delay_async(self, min_delay=2, max_delay=5):
        """Random delay between actions"""
        import random
        await asyncio.sleep(random.uniform(min_delay, max_delay))
    
    async def detect_page_state(self):
        """Detect current page state"""
        try:
            current_url = self.page.url.lower()
            page_content = await self.page.content()
            page_content_lower = page_content.lower()
            
            if "adsha.re/login" in current_url:
                return "LOGIN_REQUIRED"
            elif "adsha.re/surf" in current_url:
                if "start surfing" in page_content_lower or "surf now" in page_content_lower:
                    return "GAME_READY"
                elif "surfing" in page_content_lower or "earning" in page_content_lower:
                    return "GAME_ACTIVE"
                else:
                    return "GAME_LOADING"
            elif "adsha.re/dashboard" in current_url:
                return "DASHBOARD"
            else:
                return "UNKNOWN"
        except Exception as e:
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
                await self.send_telegram("✅ <b>ULTIMATE LOGIN SUCCESSFUL!</b>")
                return True
            elif "login" in final_url:
                logger.error("❌ LOGIN FAILED - Still on login page")
                return False
            else:
                logger.warning("⚠️ On unexpected page, but might be logged in")
                self.state['is_logged_in'] = True
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
            return True
            
        await self.page.goto(CONFIG['browser_url'], wait_until='networkidle', timeout=60000)
        await self.smart_delay_async()
        
        page_state = await self.detect_page_state()
        if page_state == "LOGIN_REQUIRED":
            logger.info("🔐 Login required, attempting automatic login...")
            return await self.force_login()
        elif page_state in ["GAME_ACTIVE", "GAME_READY", "GAME_LOADING"]:
            self.state['is_logged_in'] = True
            return True
        else:
            logger.warning(f"Unexpected page state: {page_state}")
            return await self.force_login()
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
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
            logger.error(f"BeautifulSoup parsing failed: {e}")
            return []
    
    @staticmethod
    def parse(html: str) -> List[Dict]:
        leaderboard = LeaderboardParser.parse_with_beautifulsoup(html)
        leaderboard.sort(key=lambda x: x['rank'])
        return leaderboard

# ==================== LEADERBOARD FETCHING ====================

def fetch_leaderboard() -> Optional[List[Dict]]:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
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
        logger.error(f"{Fore.RED}Network error: {e}")
        return None

# ==================== DISPLAY FUNCTIONS ====================

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def print_full_status():
    """Print clean status without banner"""
    clear_screen()
    
    # Current time and status
    tz = pytz.timezone(CONFIG['timezone'])
    current_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
    print(f"{Fore.WHITE}Time: {Fore.CYAN}{current_time}")
    
    # Browser status
    browser_status = "🟢 ACTIVE" if state.playwright_browser.state['browser_active'] else "🔴 INACTIVE"
    login_status = "✅ LOGGED IN" if state.playwright_browser.state['is_logged_in'] else "❌ NOT LOGGED IN"
    print(f"{Fore.WHITE}Browser: {Fore.GREEN if state.playwright_browser.state['browser_active'] else Fore.RED}{browser_status}")
    print(f"{Fore.WHITE}Login: {Fore.GREEN if state.playwright_browser.state['is_logged_in'] else Fore.RED}{login_status}")
    
    # Last checked
    if state.last_check_time:
        last_checked = state.last_check_time.strftime('%H:%M:%S')
        print(f"{Fore.WHITE}Last Checked: {Fore.CYAN}{last_checked}")
    
    # Check interval info
    interval_minutes = CONFIG['leaderboard_check_interval'] // 60
    print(f"{Fore.WHITE}Check Interval: {Fore.CYAN}{interval_minutes} minutes")
    
    # Status
    if state.my_position:
        if state.my_position == 1:
            pos_color = Fore.GREEN
            pos_icon = "🏆"
        else:
            pos_color = Fore.RED
            pos_icon = "📉"
        print(f"{Fore.WHITE}Position: {pos_color}{pos_icon} #{state.my_position}{Style.RESET_ALL}")
    
    # Competition Status
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}🎯 COMPETITION STATUS")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    if state.leaderboard:
        my_data = None
        for entry in state.leaderboard:
            if entry['user_id'] == CONFIG['my_user_id']:
                my_data = entry
                break
        
        if my_data:
            my_value = get_my_value(my_data)
            
            if state.my_position == 1:
                target, explanation = calculate_target(state.leaderboard)
                state.current_target = target
                
                print(f"{Fore.GREEN}✅ CURRENTLY #1!")
                print(f"{Fore.WHITE}My Credits Today: {Fore.GREEN}{my_value}")
                print(f"{Fore.WHITE}Target: {Fore.YELLOW}{target} ({explanation})")
                
                if my_value >= target:
                    print(f"{Fore.GREEN}🎯 TARGET ACHIEVED!")
                    print(f"{Fore.WHITE}Lead: {Fore.GREEN}+{my_value - target}")
                else:
                    gap = target - my_value
                    print(f"{Fore.YELLOW}🏃 CHASING TARGET")
                    print(f"{Fore.WHITE}Need: {Fore.YELLOW}{gap} more credits")
                    
                    # PREDICTION
                    if state.credits_growth_rate > 0 and gap > 0:
                        hours_needed = gap / state.credits_growth_rate
                        completion_time = datetime.now() + timedelta(hours=hours_needed)
                        
                        print(f"\n{Fore.CYAN}📈 PREDICTION")
                        print(f"{Fore.WHITE}Growth Rate: {Fore.MAGENTA}{state.credits_growth_rate:.1f} credits/hour")
                        print(f"{Fore.WHITE}ETA: {Fore.GREEN}{hours_needed:.1f} hours")
                        if hours_needed < 24:
                            print(f"{Fore.WHITE}Completion: {Fore.CYAN}{completion_time.strftime('%H:%M')}")
                        else:
                            days = hours_needed / 24
                            print(f"{Fore.WHITE}Completion: {Fore.CYAN}{days:.1f} days")
            else:
                first_place = state.leaderboard[0]
                gap = first_place['today_credits'] - my_data['today_credits']
                print(f"{Fore.RED}⚠️ NOT #1 - Currently #{state.my_position}")
                print(f"{Fore.WHITE}Leader: {Fore.YELLOW}#{first_place['user_id']}")
                print(f"{Fore.WHITE}Gap: {Fore.RED}{gap} credits")
    
    # Leaderboard with DB column
    if state.leaderboard:
        print(f"\n{Fore.CYAN}{'='*90}")
        print(f"{Fore.YELLOW}🏆 LEADERBOARD")
        print(f"{Fore.CYAN}{'='*90}{Style.RESET_ALL}")
        
        print(f"{Fore.WHITE}{'Rank':<6}{'User':<10}{'Today':<12}{'Yesterday':<12}{'DB':<12}")
        print(f"{Fore.CYAN}{'-'*60}{Style.RESET_ALL}")
        
        for entry in state.leaderboard[:8]:
            rank = entry['rank']
            user_id = entry['user_id']
            
            if user_id == CONFIG['my_user_id']:
                color = Fore.GREEN
                marker = "➤ "
            elif rank == 1:
                color = Fore.YELLOW
                marker = "🏆"
            elif rank == 2:
                color = Fore.WHITE
                marker = "🥈"
            elif rank == 3:
                color = Fore.MAGENTA
                marker = "🥉"
            else:
                color = Fore.CYAN
                marker = "  "
            
            print(f"{color}{marker}{rank:<4}#{user_id:<9}"
                  f"{entry['today_credits']:<12}"
                  f"{entry['yesterday_credits']:<12}"
                  f"{entry['day_before_credits']:<12}{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}{'='*90}{Style.RESET_ALL}")

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

async def check_competition_status():
    """Single competition check"""
    
    current_time = datetime.now()
    state.last_check_time = current_time
    
    leaderboard = fetch_leaderboard()
    if not leaderboard:
        logger.error(f"{Fore.RED}Failed to fetch leaderboard")
        if not state.playwright_browser.state['browser_active']:
            await start_browser()
        print_full_status()
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
        logger.error(f"{Fore.RED}User #{CONFIG['my_user_id']} not in top 10!")
        if not state.playwright_browser.state['browser_active']:
            await start_browser()
        print_full_status()
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
    
    # Competition logic - SINGLE DECISION
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
    
    # Single status display
    print_full_status()

# ==================== BROWSER MANAGEMENT ====================

async def start_browser():
    """Start Firefox browser"""
    if state.playwright_browser.state['browser_active']:
        return True
    
    try:
        logger.info("🚀 Starting Firefox browser...")
        
        if await state.playwright_browser.setup_browser():
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
        requests.post(url, data=data, timeout=15)
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
            requests.post(url, files=files, data=data, timeout=30)
        
        # Clean up screenshot file
        os.remove(photo_path)
        logger.info("✅ Screenshot sent and cleaned up")
        
    except Exception as e:
        logger.error(f"❌ Telegram photo failed: {e}")

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

# ==================== MAIN LOOP ====================

async def main_loop():
    """Main monitoring loop"""
    print_full_status()
    
    logger.info(f"{Fore.GREEN}AdShare Monitor v7.0 - Playwright Edition STARTED")
    logger.info(f"{Fore.CYAN}Using Playwright Firefox with profile management")
    
    send_telegram_message("🚀 <b>AdShare Monitor v7.0 Started!</b>\nPlaywright Firefox Edition")
    
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
            logger.info(f"{Fore.YELLOW}Shutting down...")
            await stop_browser()
            break
        except Exception as e:
            logger.error(f"{Fore.RED}Main loop error: {e}")
            await asyncio.sleep(30)

def signal_handler(sig, frame):
    logger.info(f"{Fore.YELLOW}Shutdown signal received")
    asyncio.create_task(stop_browser())
    sys.exit(0)

# ==================== COLAB TEST FUNCTION ====================

async def test_colab():
    """Test function for Google Colab"""
    print("🧪 Testing AdShare Monitor in Colab...")
    
    # Test profile download
    profile_manager = FirefoxProfileManager()
    profile_dir = profile_manager.get_profile_directory()
    print(f"Profile directory: {profile_dir}")
    
    # Test browser setup
    browser = PlaywrightBrowser()
    if await browser.setup_browser():
        print("✅ Browser setup successful")
        
        # Test login
        if await browser.force_login():
            print("✅ Login successful")
            
            # Take screenshot
            screenshot = await browser.take_screenshot()
            if screenshot:
                print(f"✅ Screenshot taken: {screenshot}")
            
            await browser.close()
        else:
            print("❌ Login failed")
            await browser.close()
    else:
        print("❌ Browser setup failed")

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # For Colab testing
    if 'COLAB_GPU' in os.environ:
        asyncio.run(test_colab())
    else:
        # Start Telegram bot in background
        import threading
        def run_telegram_bot():
            asyncio.run(telegram_bot_loop())
        
        bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
        bot_thread.start()
        
        # Start main loop
        asyncio.run(main_loop())
