from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QMessageBox
)
from PyQt5.QtCore import QTimer, pyqtSignal
import sqlite3
from datetime import datetime

# ==========================
# DB HELPER - LOAD ON DEMAND
# ==========================
def get_product(class_name):
    """Load produk dari database hanya saat diperlukan"""
    conn = sqlite3.connect('kasir.db')
    cursor = conn.cursor()
    cursor.execute('SELECT product_name, price FROM products WHERE class_name = ?', (class_name,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"name": row[0], "price": row[1]}
    return None

def save_transaction(customer_name, items, total):
    """Simpan transaksi ke database"""
    conn = sqlite3.connect('kasir.db')
    cursor = conn.cursor()
    
    # Simpan header transaksi
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO transactions (customer_name, total, transaction_date)
        VALUES (?, ?, ?)
    ''', (customer_name, total, timestamp))
    
    transaction_id = cursor.lastrowid
    
    # Simpan detail items
    for class_name, qty in items.items():
        product = get_product(class_name)
        if product:
            cursor.execute('''
                INSERT INTO transaction_items (transaction_id, class_name, product_name, quantity, price)
                VALUES (?, ?, ?, ?, ?)
            ''', (transaction_id, class_name, product['name'], qty, product['price']))
    
    conn.commit()
    conn.close()

# ==========================
# CART
# ==========================
class CartManager:
    def __init__(self):
        self.items = {}
        self.products_cache = {}

    def add(self, key):
        # Load produk dari DB hanya jika belum di cache
        if key not in self.products_cache:
            product = get_product(key)
            if product:
                self.products_cache[key] = product
            else:
                return  # Produk tidak ditemukan
        
        self.items[key] = self.items.get(key, 0) + 1

    def set_counts(self, counts: dict):
        # Ensure products data exists in cache
        for key in counts.keys():
            if key not in self.products_cache:
                product = get_product(key)
                if product:
                    self.products_cache[key] = product
        # Replace current items with live counts
        self.items = {k: int(v) for k, v in counts.items() if v > 0}

    def clear(self):
        self.items.clear()
        self.products_cache.clear()

    def total(self):
        return sum(self.products_cache[k]["price"] * v for k, v in self.items.items())

# ==========================
# UI
# ==========================
class KasirApp(QMainWindow):
    # SIGNAL (THREAD SAFE)
    sig_set_customer = pyqtSignal(str)
    sig_add_item = pyqtSignal(str)
    sig_set_counts = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kasirless AI")
        self.resize(800, 500)

        self.cart = CartManager()
        self.current_customer = "Unknown"

        # ---- Widgets ----
        self.lblCustomer = QLabel("Customer: Unknown")
        self.lblTotal = QLabel("Total: Rp 0")
        self.lblTotal.setStyleSheet("font-size:18px;font-weight:bold")

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Item", "Qty", "Harga", "Subtotal"]
        )
        header = self.table.horizontalHeader()
        if header:
            header.setStretchLastSection(True)

        self.btnPay = QPushButton("BAYAR")
        self.btnReset = QPushButton("RESET")

        self.btnPay.clicked.connect(self.pay)
        self.btnReset.clicked.connect(self.reset)

        # ---- Layout ----
        left = QVBoxLayout()
        left.addWidget(self.lblCustomer)
        left.addWidget(self.table)
        left.addWidget(self.lblTotal)

        right = QVBoxLayout()
        right.addWidget(self.btnPay)
        right.addWidget(self.btnReset)
        right.addStretch()

        root = QHBoxLayout()
        root.addLayout(left, 3)
        root.addLayout(right, 1)

        w = QWidget()
        w.setLayout(root)
        self.setCentralWidget(w)

        # ---- Signals ----
        self.sig_set_customer.connect(self.set_customer)
        self.sig_add_item.connect(self.add_item)
        self.sig_set_counts.connect(self.set_counts)

        # ---- Refresh Timer ----
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)

    # ==========================
    # UI UPDATE
    # ==========================
    def refresh(self):
        self.table.setRowCount(0)
        for key, qty in self.cart.items.items():
            p = self.cart.products_cache.get(key)
            if p:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(p["name"]))
                self.table.setItem(r, 1, QTableWidgetItem(str(qty)))
                self.table.setItem(r, 2, QTableWidgetItem(f"Rp {p['price']:,}"))
                self.table.setItem(r, 3, QTableWidgetItem(f"Rp {p['price'] * qty:,}"))

        self.lblTotal.setText(f"Total: Rp {self.cart.total():,}")

    # ==========================
    # SLOTS
    # ==========================
    def set_customer(self, name):
        self.lblCustomer.setText(f"Customer: {name}")
        self.current_customer = name

    def add_item(self, item):
        self.cart.add(item)

    def set_counts(self, counts: dict):
        self.cart.set_counts(counts)

    def pay(self):
        total = self.cart.total()
        if total > 0:
            customer = getattr(self, 'current_customer', 'Unknown')
            save_transaction(customer, self.cart.items, total)
            print(f"[PAY] {customer} - Total Rp {total:,} - Tersimpan ke database")
            QMessageBox.information(
                self,
                "Pembayaran Berhasil",
                f"Terima kasih, {customer}!\nTotal: Rp {total:,}"
            )
        self.reset()

    def reset(self):
        self.cart.clear()
        self.lblCustomer.setText("Customer: Unknown")
        self.current_customer = "Unknown"
