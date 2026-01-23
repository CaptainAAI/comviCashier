import sys
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtCore import Qt as QtCore
from datetime import datetime

# ==========================
# HISTORY VIEWER APP
# ==========================
class HistoryViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("History Transaksi - Kasirless AI")
        self.resize(1000, 600)
        
        # ---- Widgets ----
        self.lblTitle = QLabel("📊 RIWAYAT TRANSAKSI")
        self.lblTitle.setStyleSheet("font-size:20px;font-weight:bold;color:#2c3e50")
        self.lblTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lblStats = QLabel("Total Transaksi: 0 | Total Pendapatan: Rp 0")
        self.lblStats.setStyleSheet("font-size:14px;color:#34495e;margin:10px")
        
        # Filter customer
        self.lblFilter = QLabel("Filter Customer:")
        self.cmbCustomer = QComboBox()
        self.cmbCustomer.addItem("-- Semua Customer --")
        self.cmbCustomer.currentIndexChanged.connect(self.load_transactions)
        
        self.btnRefresh = QPushButton("🔄 Refresh")
        self.btnRefresh.clicked.connect(self.load_transactions)
        
        # Tabel transaksi
        self.tableTransactions = QTableWidget(0, 5)
        self.tableTransactions.setHorizontalHeaderLabels(
            ["ID", "Customer", "Total", "Tanggal", "Items"]
        )
        header = self.tableTransactions.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableTransactions.setSelectionBehavior(QTableWidget.SelectRows)
        self.tableTransactions.clicked.connect(self.show_transaction_detail)
        
        # Tabel detail items
        self.lblDetail = QLabel("Detail Barang:")
        self.lblDetail.setStyleSheet("font-size:14px;font-weight:bold;margin-top:10px")
        
        self.tableItems = QTableWidget(0, 4)
        self.tableItems.setHorizontalHeaderLabels(
            ["Produk", "Qty", "Harga Satuan", "Subtotal"]
        )
        headerItems = self.tableItems.horizontalHeader()
        if headerItems:
            headerItems.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # ---- Layout ----
        filterLayout = QHBoxLayout()
        filterLayout.addWidget(self.lblFilter)
        filterLayout.addWidget(self.cmbCustomer)
        filterLayout.addWidget(self.btnRefresh)
        filterLayout.addStretch()
        
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.lblTitle)
        mainLayout.addWidget(self.lblStats)
        mainLayout.addLayout(filterLayout)
        mainLayout.addWidget(self.tableTransactions, 3)
        mainLayout.addWidget(self.lblDetail)
        mainLayout.addWidget(self.tableItems, 2)
        
        container = QWidget()
        container.setLayout(mainLayout)
        self.setCentralWidget(container)
        
        # ---- Load Data ----
        self.load_customers()
        self.load_transactions()
        
        # ---- Auto Refresh Timer (setiap 5 detik) ----
        self.timer = QTimer()
        self.timer.timeout.connect(self.auto_refresh)
        self.timer.start(5000)
    
    def auto_refresh(self):
        """Auto refresh dengan load customers dulu"""
        self.load_customers()
        self.load_transactions()
    
    # ==========================
    # LOAD DATA
    # ==========================
    def load_customers(self):
        """Load daftar customer yang pernah transaksi"""
        conn = sqlite3.connect('kasir.db')
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT customer_name FROM transactions ORDER BY customer_name')
        customers = cursor.fetchall()
        conn.close()
        
        # Clear dan isi ulang combo box (BLOCK SIGNAL untuk hindari recursion)
        current_text = self.cmbCustomer.currentText()
        self.cmbCustomer.blockSignals(True)
        self.cmbCustomer.clear()
        self.cmbCustomer.addItem("-- Semua Customer --")
        for (customer,) in customers:
            self.cmbCustomer.addItem(customer)
        
        # Restore selection
        index = self.cmbCustomer.findText(current_text)
        if index >= 0:
            self.cmbCustomer.setCurrentIndex(index)
        self.cmbCustomer.blockSignals(False)
    
    def load_transactions(self):
        """Load semua transaksi dari database"""
        conn = sqlite3.connect('kasir.db')
        cursor = conn.cursor()
        
        # Filter berdasarkan customer
        customer_filter = self.cmbCustomer.currentText()
        if customer_filter == "-- Semua Customer --":
            cursor.execute('''
                SELECT id, customer_name, total, transaction_date 
                FROM transactions 
                ORDER BY id DESC
            ''')
        else:
            cursor.execute('''
                SELECT id, customer_name, total, transaction_date 
                FROM transactions 
                WHERE customer_name = ?
                ORDER BY id DESC
            ''', (customer_filter,))
        
        transactions = cursor.fetchall()
        
        # Update tabel
        self.tableTransactions.setRowCount(0)
        total_pendapatan = 0
        
        for trans_id, customer, total, date in transactions:
            # Hitung jumlah items
            cursor.execute('SELECT COUNT(*) FROM transaction_items WHERE transaction_id = ?', (trans_id,))
            item_count = cursor.fetchone()[0]
            
            r = self.tableTransactions.rowCount()
            self.tableTransactions.insertRow(r)
            self.tableTransactions.setItem(r, 0, QTableWidgetItem(str(trans_id)))
            self.tableTransactions.setItem(r, 1, QTableWidgetItem(customer))
            self.tableTransactions.setItem(r, 2, QTableWidgetItem(f"Rp {total:,}"))
            self.tableTransactions.setItem(r, 3, QTableWidgetItem(date))
            self.tableTransactions.setItem(r, 4, QTableWidgetItem(f"{item_count} items"))
            
            total_pendapatan += total
        
        conn.close()
        
        # Update statistik
        self.lblStats.setText(
            f"Total Transaksi: {len(transactions)} | Total Pendapatan: Rp {total_pendapatan:,}"
        )
    
    def show_transaction_detail(self):
        """Tampilkan detail items dari transaksi yang dipilih"""
        selected = self.tableTransactions.currentRow()
        if selected < 0:
            return
        
        item = self.tableTransactions.item(selected, 0)
        if not item:
            return
        trans_id = int(item.text())
        
        conn = sqlite3.connect('kasir.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT product_name, quantity, price
            FROM transaction_items
            WHERE transaction_id = ?
        ''', (trans_id,))
        items = cursor.fetchall()
        conn.close()
        
        # Update tabel items
        self.tableItems.setRowCount(0)
        for product_name, qty, price in items:
            r = self.tableItems.rowCount()
            self.tableItems.insertRow(r)
            self.tableItems.setItem(r, 0, QTableWidgetItem(product_name))
            self.tableItems.setItem(r, 1, QTableWidgetItem(str(qty)))
            self.tableItems.setItem(r, 2, QTableWidgetItem(f"Rp {price:,}"))
            self.tableItems.setItem(r, 3, QTableWidgetItem(f"Rp {price * qty:,}"))

# ==========================
# MAIN
# ==========================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = HistoryViewer()
    window.show()
    sys.exit(app.exec_())
