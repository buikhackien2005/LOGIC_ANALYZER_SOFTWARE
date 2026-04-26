from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel
from ui.plot_manager import PlotManager
from ui.transaction_log import TransactionLog
from utils.mock_generator import MockDataGenerator
# Import các Decoder
from core.decoders.uart_decoder import UARTDecoder
from core.decoders.i2c_decoder import I2CDecoder
from core.decoders.spi_decoder import SPIDecoder

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Logic Analyzer - Pro Edition")
        self.resize(1300, 850)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)
        
        # --- PANEL TRÁI (Waveform + Logs) ---
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        
        self.plot_manager = PlotManager()
        self.left_layout.addWidget(self.plot_manager, stretch=7)
        
        self.btn_test_mock = QPushButton("RUN ANALYSIS: Load & Decode All")
        self.btn_test_mock.setStyleSheet("padding: 12px; background-color: #2E7D32; color: white; font-weight: bold;")
        self.btn_test_mock.clicked.connect(self.run_analysis_flow)
        self.left_layout.addWidget(self.btn_test_mock)
        
        # Nhúng Bảng Log thật vào
        self.transaction_log = TransactionLog()
        self.left_layout.addWidget(self.transaction_log, stretch=3)
        
        # --- PANEL PHẢI (Placeholders) ---
        self.placeholder_right = QLabel("[Control Panel - Next Phase]")
        self.placeholder_right.setStyleSheet("background-color: #252526; color: white; alignment: center;")
        
        self.main_layout.addWidget(self.left_panel, stretch=8)
        self.main_layout.addWidget(self.placeholder_right, stretch=2)

    def run_analysis_flow(self):
        """Luồng xử lý: Nhận data -> Vẽ sóng -> Giải mã song song -> Sắp xếp -> In Log."""
        # 1. Lấy dữ liệu
        t, buf = MockDataGenerator.get_8ch_mock_data()
        sample_rate = 500000
        
        # 2. Vẽ đồ thị
        self.plot_manager.update_data(t, buf)
        
        # 3. Tạo danh sách các Decoder (Giả định cấu hình chân)
        active_decoders = [
            UARTDecoder(tx_channel=1, baud_rate=9600),
            I2CDecoder(sda_channel=2, scl_channel=3),
            SPIDecoder(sck_channel=0, mosi_channel=4) # Giả định CH0 là Clock, CH4 là MOSI
        ]
        
        # 4. Chạy giải mã Đa hình
        all_results = []
        for decoder in active_decoders:
            try:
                res = decoder.decode(sample_rate, buf)
                all_results.extend(res)
            except Exception as e:
                print(f"Lỗi khi giải mã {type(decoder).__name__}: {e}")
        
        # 5. SẮP XẾP THEO THỜI GIAN (Rất quan trọng)
        # Chúng ta dùng 'time_val' (số thực) thay vì 'time' (chuỗi) để sort chính xác
        all_results.sort(key=lambda x: x.get('time_val', 0))
        
        # 6. Hiển thị lên bảng Log
        self.transaction_log.update_logs(all_results)