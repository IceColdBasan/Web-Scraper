#I did not write this code this is code created by Claude AI that I looked at for inspiration. DO NOT GRADE THIS FOR QUALITY OR AS MY OWN WORK.

import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
import time
from typing import List, Dict, Optional
from datetime import datetime

class GroceryScraper:
    def __init__(self, base_url: str, db_path: str = "grocery_data.db", delay: float = 1.0):
        self.base_url = base_url
        self.delay = delay
        self.db_path = db_path
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        self.init_db()

    def init_db(self):
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
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_product_url ON products(url)
        ''')
        conn.commit()
        conn.close()
        print(f"Database initialized at {self.db_path}")

        def scrapeProductPage(self, url:str) -> Dict:
            try:
                time.sleep(self.delay)
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                productData = {
                    'name': self.safeExtract(soup, 'h1.product-title'),
                    'price': self.safeExtract(soup, 'span.price'),
                    'description': self.safeExtract(soup, 'div.product-description'),
                    'category': self.safeExtract(soup, 'span.category'),
                    'in_stock': self.checkStock(soup),
                    'url': url
                }
                return productData
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}")
                return {}
        
    def safeExtract(self, soup: BeautifulSoup, selector: str) -> str:
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else "N/A"
    
    def checkStock(self, soup: BeautifulSoup) -> bool:
        stockElement = soup.select_one('span.stock-status')
        if stockElement:
            return 'in stock' in stockElement.get_text(strip=True).lower()
        return False
    
    def saveToDatabase(self, productData: Dict) -> Optional[int]:
        if not productData:
            return None
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT id, price FROM products WHERE url = ?', (productData['url'],))
            existing = cursor.fetchone()

            if existing:
                product_id, old_price = existing

                cursor.execute('''UPDATE products 
                               SET name = ?, price = ?, description = ?, category = ?, 
                               in_stock = ?, updated_at = ? WHERE id = ?''',
                               (productData['name'], 
                                productData['price'], 
                                productData['description'], 
                                productData['category'], 
                                productData['in_stock'], 
                                datetime.now(), 
                                product_id
                                ))
                
                if old_price != productData['price']:
                    cursor.execute('''INSERT INTO price_history (product_id, price, in_stock) 
                                   VALUES (?, ?, ?)''',
                                   (product_id, productData['price'], 
                                    productData['in_stock']
                                    ))
                print(f"Updated product: {productData['name']}")
            else:

                cursor.execute('''INSERT INTO products (name, price, description, category, in_stock, url) VALUES (?, ?, ?, ?, ?, ?)''',
                                 (productData['name'], 
                                  productData['price'], 
                                  productData['description'], 
                                  productData['category'], 
                                  productData['in_stock'], 
                                  productData['url']
                                  ))
                print(f"Inserted new product: {productData['name']}")

            conn.commit()
            return product_id
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def scrapeCategory(self, category_url: str) -> List[str]:
        try:
            response = requests.get(category_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            productLinks = soup.select('a.product-link')
            urls = []
            for link in productLinks:
                href = link.get('href')
                if href:
                    if href.startswith('/'):
                        href = self.base_url + href
                    urls.append(href)
            return urls
        except Exception as e:
            print(f"Error scraping category {category_url}: {e}")
            return []
        
    def scrapeAndSave(self, product_urls: List[str]):
        for i, url in enumerate(product_urls, 1):
            print(f"Scraping product {i}/{len(product_urls)}: {url}")
            productData = self.scrapeProductPage(url)
            self.saveToDatabase(productData)
    
    def getAllProducts(self) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query('SELECT * FROM products ORDER BY created_at DESC', conn)
        conn.close()
        return df
    
    def getPriceHistory(self, product_id: int) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query('SELECT * FROM price_history WHERE product_id = ? ORDER BY recorded_at DESC', conn, params=(product_id,))
        conn.close()
        return df
    
    def getProductsByCategory(self, category: str) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query('SELECT * FROM products WHERE category = ? ORDER BY created_at DESC', conn, params=(category,))
        conn.close()
        return df
    
    def searchProducts(self, searchTerm: str) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query('SELECT * FROM products WHERE name LIKE ? ORDER BY created_at DESC', conn, params=(f'%{searchTerm}%',))
        conn.close()
        return df
    
if __name__ == "__main__":
    base_url = "https://www.walmart.com/search?q=chicken%20patties"
    scraper = GroceryScraper(base_url, db_path="grocery_data.db", delay=1.0)

    print("\n Scraping and saving products to database")
    category_url = f"{base_url}/category/fruits-vegetables"
    product_urls = scraper.scrapeCategory(category_url)
    
    if product_urls:
        scraper.scrapeAndSave(product_urls[:5])  # Scrape first 5 products for demo

    print("\n Fetching all products from database")
    all_products_df = scraper.getAllProducts()
    print(all_products_df)