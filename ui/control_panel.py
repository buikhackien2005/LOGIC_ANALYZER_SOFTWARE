from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QPushButton, QLabel, QLineEdit, QStackedWidget, 
                             QFormLayout, QGroupBox, QListWidget)
from PyQt5.QtCore import pyqtSignal

class ControlPanel(QWidget):
    # Khai báo một Tín hiệu (Signal) phát ra một Dictionary chứa cấu hình
    on_decoder_added = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        # Giữ nền sáng mặc định của OS, ép chữ thành màu đen
        self.setStyleSheet("""
            QWidget {
                color: #000000;
            }
            QGroupBox {
                border: 1px solid #AAA;
                margin-top: 15px;
                font-weight: bold;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # === PHẦN 1: FORM THÊM DECODER ===
        group_add = QGroupBox("Add New Decoder")
        group_add.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #555; margin-top: 10px; padding-top: 15px;}")
        add_layout = QVBoxLayout(group_add)

        # 1.1 Chọn giao thức
        self.combo_protocol = QComboBox()
        self.combo_protocol.addItems(["UART", "I2C", "SPI"])
        self.combo_protocol.setStyleSheet("background-color: #333; padding: 5px;")
        self.combo_protocol.currentIndexChanged.connect(self.change_config_page)
        add_layout.addWidget(QLabel("Protocol:"))
        add_layout.addWidget(self.combo_protocol)

        # 1.2 Các trang cài đặt động (Stacked Widget)
        self.stacked_config = QStackedWidget()
        self.setup_uart_page()
        self.setup_i2c_page()
        self.setup_spi_page()
        add_layout.addWidget(self.stacked_config)

        # 1.3 Nút Add
        self.btn_add = QPushButton("ADD TO PIPELINE")
        self.btn_add.setStyleSheet("background-color: #007ACC; padding: 8px; font-weight: bold;")
        self.btn_add.clicked.connect(self.emit_decoder_config)
        add_layout.addWidget(self.btn_add)

        layout.addWidget(group_add)

        # === PHẦN 2: DANH SÁCH DECODER ĐANG CHẠY ===
        group_list = QGroupBox("Active Decoders")
        group_list.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #555; margin-top: 10px; padding-top: 15px;}")
        list_layout = QVBoxLayout(group_list)
        
        self.list_active = QListWidget()
        self.list_active.setStyleSheet("background-color: #1E1E1E; border: none;")
        list_layout.addWidget(self.list_active)

        self.btn_clear = QPushButton("Clear All Decoders")
        self.btn_clear.setStyleSheet("background-color: #B71C1C; padding: 5px;")
        # Sẽ kết nối sự kiện xóa sau
        list_layout.addWidget(self.btn_clear)

        layout.addWidget(group_list)
        layout.addStretch() # Đẩy mọi thứ lên trên cùng

    # --- CÁC HÀM TẠO GIAO DIỆN CON ---
    def get_channel_combo(self):
        cb = QComboBox()
        cb.addItems([f"CH{i}" for i in range(8)])
        cb.setStyleSheet("background-color: #333;")
        return cb

    def setup_uart_page(self):
        page = QWidget()
        lay = QFormLayout(page)
        self.uart_tx = self.get_channel_combo()
        self.uart_tx.setCurrentIndex(1) # Mặc định CH1
        self.uart_baud = QLineEdit("9600")
        self.uart_baud.setStyleSheet("background-color: #333; padding: 2px;")
        lay.addRow("TX Channel:", self.uart_tx)
        lay.addRow("Baudrate:", self.uart_baud)
        self.stacked_config.addWidget(page)

    def setup_i2c_page(self):
        page = QWidget()
        lay = QFormLayout(page)
        self.i2c_sda = self.get_channel_combo()
        self.i2c_sda.setCurrentIndex(2)
        self.i2c_scl = self.get_channel_combo()
        self.i2c_scl.setCurrentIndex(3)
        lay.addRow("SDA Channel:", self.i2c_sda)
        lay.addRow("SCL Channel:", self.i2c_scl)
        self.stacked_config.addWidget(page)

    def setup_spi_page(self):
        page = QWidget()
        lay = QFormLayout(page)
        self.spi_sck = self.get_channel_combo()
        self.spi_sck.setCurrentIndex(0)
        self.spi_mosi = self.get_channel_combo()
        self.spi_mosi.setCurrentIndex(4)
        lay.addRow("SCK Channel:", self.spi_sck)
        lay.addRow("MOSI Channel:", self.spi_mosi)
        self.stacked_config.addWidget(page)

    # --- CÁC HÀM XỬ LÝ SỰ KIỆN ---
    def change_config_page(self, index):
        self.stacked_config.setCurrentIndex(index)

    def emit_decoder_config(self):
        """Gói thông tin cài đặt và ném (emit) ra ngoài cho MainWindow bắt."""
        protocol = self.combo_protocol.currentText()
        config = {'protocol': protocol}

        if protocol == "UART":
            config['tx'] = self.uart_tx.currentIndex()
            config['baud'] = int(self.uart_baud.text() or 9600)
            display_text = f"UART (TX: CH{config['tx']}, {config['baud']}bps)"
            
        elif protocol == "I2C":
            config['sda'] = self.i2c_sda.currentIndex()
            config['scl'] = self.i2c_scl.currentIndex()
            display_text = f"I2C (SDA: CH{config['sda']}, SCL: CH{config['scl']})"
            
        elif protocol == "SPI":
            config['sck'] = self.spi_sck.currentIndex()
            config['mosi'] = self.spi_mosi.currentIndex()
            display_text = f"SPI (SCK: CH{config['sck']}, MOSI: CH{config['mosi']})"

        # Hiển thị lên danh sách bên dưới để người dùng thấy
        self.list_active.addItem(display_text)
        
        # Bắn tín hiệu mang theo từ điển (dict) cấu hình ra ngoài
        self.on_decoder_added.emit(config)