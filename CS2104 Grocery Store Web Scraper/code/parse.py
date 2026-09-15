import pandas as pd
from bs4 import BeautifulSoup
import sqlite3
import os
import re

# Configures pandas display options for better readability
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', None)

# VERY IMPORTANT: Change the html_dir variable to test different HTML files
html_dir = "./data/test7.html"


# Reads the HTML file and initializes BeautifulSoup for parsing
file = open(html_dir, "r", encoding="utf-8")
soup = BeautifulSoup(file, "html.parser")

# Clears the existing database file if it exists
def clearDatabase():
    if os.path.exists("./data/products.db"):
        os.remove("./data/products.db")
        print("Database cleared successfully.")
    else:
        print("Database does not exist.")
clearDatabase()

# Initializes the SQL database and creates the necessary table
def initDataBase():
    conn = sqlite3.connect("./data/products.db")
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS GroceryProducts(
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL,
                          price REAL NOT NULL,
                        pricePerOz REAL NOT NULL,
                          rating REAL NOT NULL
                   )''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# Inserts a product into the database using SQL
def insertProduct(name, price, pricePerOz, rating):
    conn = sqlite3.connect("./data/products.db")
    cursor = conn.cursor()

    cursor.execute('''
                   INSERT INTO GroceryProducts (name, price, pricePerOz, rating)
                   VALUES (?, ?, ?, ?)''', (name, price, pricePerOz, rating))
    conn.commit()
    conn.close()
    print(f"Inserted product: {name}, Price: {price}, PricePerOz: {pricePerOz}, Rating: {rating}")

# Retrieves all products from the database and returns them as a pandas DataFrame
def getAllProducts() -> pd.DataFrame:
        conn = sqlite3.connect("./data/products.db")
        # Adjust this query to change the different categories
        df = pd.read_sql_query('SELECT * FROM GroceryProducts ORDER BY price ASC', conn)
        conn.close()
        return df
initDataBase()

# Parses the HTML and extracts product information based on the structure of the HTML file (Simple HTML)
if (html_dir == "./data/test.html"):
    name = soup.find_all("h4")
    ratings = soup.find_all(class_="rating")
    prices = soup.find_all(class_="price")
    for i in range(0, len(name), 3):
        if(name[i].get_text().strip() == ""):
            continue
        product_name = name[i].get_text().strip()[:int(re.search(r'\d+', name[i].get_text().strip()).start()) - 2]
        product_price = float(prices[i + 1].get_text().strip().replace("$", ""))
        product_rating = float(ratings[i].get_text().strip()[0:3])
        product_pricePerOz = float( product_price / int(re.search(r'\d+', name[i].get_text().strip()).group(0)))
        insertProduct(product_name, product_price, product_pricePerOz, product_rating)

# Parses the HTML and extracts product information based on the structure of the HTML file (WALMART)
if (html_dir == "./data/test2.html" or html_dir == "./data/test3.html" or html_dir == "./data/test6.html"):
    Run = True
    #Uses Walmarts class name to find product information
    name = soup.find_all(class_="w_iUH7")
    #Loops through skipping every 3 elements to get name, price, and rating
    for i in range(0, len(name), 3):
        if(name[i].get_text().strip() == ""):
            continue
        product_name = name[i].get_text().strip()
        product_price = float(name[i + 1].get_text().strip()[name[i+1].get_text().strip().find("$")+1:])
        if (name[i + 2].get_text().strip()[0:3] != ""):
            product_rating = float(name[i + 2].get_text().strip()[0:3])
        else:
            product_rating = 0.0
        
        if not (re.search(r'\d+\so', name[i].get_text().strip().lower()) is None):
            product_pricePerOz = float( product_price / int(re.search(r'\d+\so', name[i].get_text().strip().lower()).group(0)[:re.search(r'\d+\so', name[i].get_text().strip().lower()).group(0).find("o") - 1]))
        else:
            product_pricePerOz = 0.0
            Run = False
        if(Run):
            if(product_name[:int(re.search(r'\d+\so', name[i].get_text().strip().lower()).start()) + 2].find(".") == -1):
                product_name = name[i].get_text().strip()[:int(re.search(r'\d+\so', name[i].get_text().strip().lower()).start()) - 2]
            else:
                product_name = name[i].get_text().strip()[:int(re.search(r'\d+\so', name[i].get_text().strip().lower()).start()) - 5]

        insertProduct(product_name, product_price, product_pricePerOz, product_rating)

# Parses the HTML and extracts product information based on the structure of the HTML file (KROGER)
if(html_dir == "./data/test4.html" or html_dir == "./data/test5.html" or html_dir == "./data/test7.html"):
    # Uses Kroger's class names to find product information
    name = soup.find_all(class_="kds-Link kds-Link--inherit kds-Link--implied ProductDescription-truncated overflow-hidden text-primary")
    prices = soup.find_all(class_ = "kds-Price kds-Price--alternate")
    product_pricePerOz = soup.find_all(class_ = "kds-Text--s text-neutral-more-prominent")

    #Loops through each product to extract and clean the data
    for i in range(0, len(name)):
        product_name = name[i]['aria-label'].strip()
        product_name = re.sub(r'[^a-zA-Z0-9\s\.]', '', product_name)
        if not (re.search(r'[a-zA-Z]\s\d', product_name) is None):
            product_name = product_name[::-1]
            product_name = product_name[re.search(r'\d\s\w', product_name).end() - 1:][::-1].strip()
        else:
            product_name = product_name[:re.search(r'title', product_name).start() - 1].strip()
        price = prices[i]['value']
        pricePerOz = product_pricePerOz[i].get_text().strip()
        if(pricePerOz.find("lb") != -1):
            if(pricePerOz.find("$") != -1):
                pricePerOz = float(pricePerOz[pricePerOz.find("$")+1:pricePerOz.find("/lb")]) / 16
            else:
                pricePerOz = float(price) / (int(re.search(r'\d+', pricePerOz).group(0)) * 16)
        if(not isinstance(pricePerOz, float) and pricePerOz.lower().find("oz") != -1):
            if(pricePerOz.find("$") != -1):
                pricePerOz = float(pricePerOz[pricePerOz.find("$")+1:pricePerOz.find("/oz")])
            else:
                pricePerOz = float(price) / int(re.search(r'\d+', pricePerOz).group(0))
        insertProduct(product_name, price, pricePerOz, 0)

    product_rating = 0

# Retrieves all products from the database, prints them, and saves them to a JSON file
dataFrame = getAllProducts()
print(dataFrame)
dataFrame.to_json("./data/products.json", orient="records")

file.close()
