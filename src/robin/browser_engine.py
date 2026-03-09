import logging
import time
import random
import os
from typing import Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
from .config import TOR_SOCKS_HOST, TOR_SOCKS_PORT

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Singleton manager for undetected-chromedriver instances.
    Handles stealth, Tor-SOCKS routing, and automatic cleanup.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
            cls._instance.driver = None
            cls._instance.ua = UserAgent()
        return cls._instance

    def get_driver(self, force_new: bool = False) -> uc.Chrome:
        """
        Returns an undetected chrome driver instance.
        """
        if self.driver and not force_new:
            try:
                # Check if driver is still alive
                self.driver.current_url
                return self.driver
            except Exception:
                self.quit_driver()

        logger.info("Initializing new undetected-chromedriver instance with stealth patches...")
        
        options = uc.ChromeOptions()
        # Headless mode
        options.add_argument("--headless")
        
        # Random User-Agent
        options.add_argument(f"--user-agent={self.ua.random}")
        
        # Tor-SOCKS integration
        options.add_argument(f"--proxy-server=socks5://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}")
        
        # Disable images/extensions
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        try:
            self.driver = uc.Chrome(options=options, version_main=135)
            
            # Inject Canvas Fingerprint Noise
            self._inject_stealth_scripts(self.driver)
            
            return self.driver
        except Exception as e:
            logger.error(f"Failed to initialize UC driver: {e}")
            return None

    def _inject_stealth_scripts(self, driver: uc.Chrome):
        """
        Injects JS to add noise to canvas and override common headless detections.
        """
        script = """
        // Overwrite the `languages` property to use a common list
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });

        // Add noise to Canvas fingerprinting
        const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
            const imageData = originalGetImageData.apply(this, arguments);
            const data = imageData.data;
            for (let i = 0; i < data.length; i += 4) {
                // Add tiny, invisible noise
                data[i] = data[i] + (Math.random() > 0.5 ? 1 : -1);
            }
            return imageData;
        };
        """
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})
        except Exception as e:
            logger.warning(f"Failed to inject stealth scripts: {e}")

    def quit_driver(self):
        """
        Safely terminates the browser instance.
        """
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
            logger.info("UC driver terminated.")

    def scrape_url(self, url: str, wait_for_selector: Optional[str] = None, timeout: int = 30) -> Optional[str]:
        """
        Navigates to a URL, waits for optional content, and returns page source.
        """
        driver = self.get_driver()
        if not driver:
            return None

        try:
            logger.info(f"Navigating to {url} via UC...")
            driver.get(url)
            
            if wait_for_selector:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                )
            else:
                # Basic sleep to allow JS challenges/renders
                time.sleep(random.uniform(3, 6))
            
            return driver.page_source
        except Exception as e:
            logger.error(f"Error scraping {url} via UC: {e}")
            return None

# Global instance
browser_manager = BrowserManager()
