import sqlite3

# ==========================
# INIT DATABASE
# ==========================
def init_database():
    conn = sqlite3.connect('kasir.db')
    cursor = conn.cursor()
    
    # Buat tabel products
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT UNIQUE NOT NULL,
            product_name TEXT NOT NULL,
            price INTEGER NOT NULL
        )
    ''')
    
    # Buat tabel transactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            total INTEGER NOT NULL,
            transaction_date TEXT NOT NULL
        )
    ''')
    
    # Buat tabel transaction_items
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            class_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price INTEGER NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
    ''')
    
    # Data produk dengan harga real (2025)
    products = [
        ('BigRolls', 'Big Rolls Wafer', 2500),
        ('BrowniesCruunchy', 'Brownies Crunchy', 3500),
        ('Gery', 'Gery Saluut', 1500),
        ('Lexus', 'Lexus Wafer', 2000),
        ('Milkita', 'Milkita Lolipop', 1000),
        ('Momotaro', 'Momotaro Snack', 2000),
        ('Pocky', 'Pocky Stick', 8000),
        ('RomaSandwich', 'Roma Sandwich Biskuit', 2500),
        ('SlaiOlai', 'Slai Olai', 5000),
        ('Soyjoy', 'Soyjoy Bar', 6000),
        ('garuda', 'Kacang Garuda', 3000),
    ]
    
    # Insert data (ignore jika sudah ada)
    for class_name, product_name, price in products:
        cursor.execute('''
            INSERT OR IGNORE INTO products (class_name, product_name, price)
            VALUES (?, ?, ?)
        ''', (class_name, product_name, price))
    
    conn.commit()
    conn.close()
    print("[OK] Database kasir.db berhasil dibuat!")
    print("[OK] 11 produk jajan berhasil ditambahkan")
    print("[OK] Tabel transactions dan transaction_items siap")

if __name__ == '__main__':
    init_database()
