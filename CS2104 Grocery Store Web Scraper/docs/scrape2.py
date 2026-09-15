#I did not write this code this is code created by Claude AI that I looked at for inspiration. DO NOT GRADE THIS FOR QUALITY OR AS MY OWN WORK.

import pandas as pd
import sqlite3
import time
from typing import List, Dict, Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import random

class GroceryScraper:
    def __init__(self, base_url: str, db_path: str = "grocery_data.db", delay: float = 2.0, headless: bool = False):
        """
        Initialize the scraper with database connection and Selenium
        
        Args:
            base_url: Base URL of the grocery website
            db_path: Path to SQLite database file
            delay: Delay between requests in seconds
            headless: Run browser in headless mode (recommended: False for Walmart)
        """
        self.base_url = base_url
        self.delay = delay
        self.db_path = db_path
        self.headless = headless
        self._init_database()
    
    def _init_driver(self):
        """Initialize Selenium WebDriver with anti-detection measures"""
        chrome_options = Options()
        
        # Anti-detection settings
        if self.headless:
            chrome_options.add_argument('--headless=new')  # Use new headless mode
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--lang=en-US')
        
        # Realistic user agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Window size
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--start-maximized')
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            
            # Execute CDP commands to hide automation
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except Exception as e:
            print(f"Error initializing driver: {e}")
            print("\nMake sure ChromeDriver is installed:")
            print("pip install webdriver-manager")
            print("Or download from: https://chromedriver.chromium.org/")
            raise
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price TEXT,
                description TEXT,
                category TEXT,
                in_stock BOOLEAN,
                url TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                price TEXT,
                in_stock BOOLEAN,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        cursor.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'url' not in columns:
            print("Migrating database: adding url column...")
            cursor.execute('ALTER TABLE products ADD COLUMN url TEXT')
            conn.commit()
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_product_url ON products(url)
        ''')
        
        conn.commit()
        conn.close()
        print(f"Database initialized: {self.db_path}")
    
    def _human_like_delay(self):
        """Add random human-like delay"""
        time.sleep(random.uniform(self.delay, self.delay + 2))
    
    def _scroll_slowly(self, driver):
        """Scroll page slowly like a human"""
        total_height = driver.execute_script("return document.body.scrollHeight")
        viewport_height = driver.execute_script("return window.innerHeight")
        current_position = 0
        
        while current_position < total_height:
            # Scroll by random amount
            scroll_amount = random.randint(300, 700)
            current_position += scroll_amount
            driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(random.uniform(0.5, 1.5))
            
            # Update total height in case new content loaded
            total_height = driver.execute_script("return document.body.scrollHeight")
            
            if current_position >= total_height:
                break
    
    def scrape_products_from_listing(self, listing_url: str, max_products: int = 20) -> List[Dict]:
        """
        Scrape multiple products from a Walmart listing page using Selenium
        
        Args:
            listing_url: URL of the Walmart listing/category page
            max_products: Maximum number of products to scrape (to avoid detection)
            
        Returns:
            List of product dictionaries
        """
        driver = None
        try:
            print(f"Initializing browser (non-headless for better bot evasion)...")
            driver = self._init_driver()
            
            print(f"Loading page: {listing_url}")
            driver.get(listing_url)
            
            # Random delay to mimic human behavior
            print("Waiting like a human...")
            time.sleep(random.uniform(3, 5))
            
            # Wait for products to load
            print("Waiting for products to appear...")
            try:
                wait = WebDriverWait(driver, 60)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.w_iUH7')))
                print("Products loaded!")
            except Exception as e:
                print(f"Timeout waiting for products. Page might be blocked.")
                # Save screenshot for debugging
                driver.save_screenshot("walmart_blocked.png")
                print("Screenshot saved as 'walmart_blocked.png' - check if bot detection triggered")
                return []
            
            # Scroll slowly to load more products
            print("Scrolling page slowly...")
            self._scroll_slowly(driver)
            
            # Small delay after scrolling
            time.sleep(random.uniform(2, 4))
            
            # Get page source and parse
            print("Parsing page content...")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all product containers
            product_containers = soup.find_all('div', {'role': 'group', 'data-item-id': True})
            
            print(f"Found {len(product_containers)} product containers")
            
            if len(product_containers) == 0:
                print("No products found. Walmart may have blocked the request.")
                driver.save_screenshot("no_products_found.png")
                print("Screenshot saved - check for CAPTCHA or blocking message")
                
                # Print page title for debugging
                print(f"Page title: {driver.title}")
                return []
            
            products = []
            
            for idx, container in enumerate(product_containers[:max_products], 1):
                try:
                    # Find product name
                    name_element = container.find('span', class_='w_iUH7')
                    if not name_element:
                        continue
                    
                    name = name_element.get_text(strip=True)
                    if not name or len(name) < 5:
                        continue
                    
                    # Find price
                    price = "N/A"
                    price_container = container.find('div', {'data-automation-id': 'product-price'})
                    if price_container:
                        price_parts = price_container.find_all('span')
                        for span in price_parts:
                            text = span.get_text(strip=True)
                            if '$' in text and any(c.isdigit() for c in text):
                                import re
                                price_match = re.search(r'\$?(\d+)\.?(\d{0,2})', text)
                                if price_match:
                                    dollars = price_match.group(1)
                                    cents = price_match.group(2).ljust(2, '0') if price_match.group(2) else '00'
                                    price = f"${dollars}.{cents}"
                                    break
                    
                    # Find URL
                    link = container.find('a', href=True)
                    product_url = "N/A"
                    if link and link.get('href'):
                        href = link.get('href')
                        product_url = href if href.startswith('http') else self.base_url + href
                    
                    product_data = {
                        'name': name,
                        'price': price,
                        'description': "N/A",
                        'category': "N/A",
                        'in_stock': True,
                        'url': product_url
                    }
                    products.append(product_data)
                    print(f"  ✓ [{idx}/{min(len(product_containers), max_products)}] {name} - {price}")
                    
                except Exception as e:
                    print(f"  Error parsing product {idx}: {e}")
                    continue
            
            print(f"\n Successfully scraped {len(products)} products")
            return products
            
        except Exception as e:
            print(f"Error scraping: {e}")
            if driver:
                driver.save_screenshot("error_screenshot.png")
                print("Error screenshot saved")
            return []
        finally:
            if driver:
                print("Closing browser...")
                time.sleep(2)  # Let things settle before closing
                driver.quit()
    
    def save_product_to_db(self, product_data: Dict) -> Optional[int]:
        """Save product data to database"""
        if not product_data:
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id, price FROM products WHERE url = ?', 
                         (product_data['url'],))
            existing = cursor.fetchone()
            
            if existing:
                product_id, old_price = existing
                cursor.execute('''
                    UPDATE products 
                    SET name = ?, price = ?, description = ?, category = ?, 
                        in_stock = ?, updated_at = ?
                    WHERE id = ?
                ''', (
                    product_data['name'],
                    product_data['price'],
                    product_data['description'],
                    product_data['category'],
                    product_data['in_stock'],
                    datetime.now(),
                    product_id
                ))
                
                if old_price != product_data['price']:
                    cursor.execute('''
                        INSERT INTO price_history (product_id, price, in_stock)
                        VALUES (?, ?, ?)
                    ''', (product_id, product_data['price'], product_data['in_stock']))
            else:
                cursor.execute('''
                    INSERT INTO products (name, price, description, category, in_stock, url)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    product_data['name'],
                    product_data['price'],
                    product_data['description'],
                    product_data['category'],
                    product_data['in_stock'],
                    product_data['url']
                ))
                product_id = cursor.lastrowid
                
                cursor.execute('''
                    INSERT INTO price_history (product_id, price, in_stock)
                    VALUES (?, ?, ?)
                ''', (product_id, product_data['price'], product_data['in_stock']))
            
            conn.commit()
            return product_id
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_all_products(self) -> pd.DataFrame:
        """Retrieve all products from database"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query('SELECT * FROM products ORDER BY created_at DESC', conn)
        conn.close()
        return df
    
    def search_products(self, search_term: str) -> pd.DataFrame:
        """Search products by name"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT * FROM products 
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY name
        '''
        search_pattern = f'%{search_term}%'
        df = pd.read_sql_query(query, conn, params=(search_pattern, search_pattern))
        conn.close()
        return df
    
    def export_to_csv(self, filename: str):
        """Export all products to CSV"""
        df = self.get_all_products()
        df.to_csv(filename, index=False)
        print(f"✅ Exported {len(df)} products to {filename}")


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("WALMART GROCERY SCRAPER")
    print("=" * 60)
    
    # Initialize scraper (headless=False to avoid detection)
    scraper = GroceryScraper("https://www.walmart.com", db_path="walmart_groceries.db", headless=False)
    
    # Scrape Walmart search results
    walmart_url = "https://www.walmart.com/search?q=chicken+patties"
    products = scraper.scrape_products_from_listing(walmart_url, max_products=15)
    
    if products:
        # Save to database
        print("\nSaving to database...")
        for product in products:
            scraper.save_product_to_db(product)
        
        # View results
        print("\nProducts in database:")
        df = scraper.get_all_products()
        print(df[['name', 'price']].to_string(index=False))
        
        # Export to CSV
        print("\n")
        scraper.export_to_csv("walmart_products.csv")
    else:
        print("\nNo products scraped. Check screenshots for debugging.")