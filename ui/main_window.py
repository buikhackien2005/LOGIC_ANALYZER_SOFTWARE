from core.serial_reader import SerialReaderThread
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from ui.plot_manager import PlotManager
from ui.transaction_log import TransactionLog
from ui.control_panel import ControlPanel
from utils.mock_generator import MockDataGenerator

# Import các lớp giải mã từ lõi hệ thống
from core.decoders.uart_decoder import UARTDecoder
from core.decoders.i2c_decoder import I2CDecoder
from core.decoders.spi_decoder import SPIDecoder

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Logic Analyzer - Pro Edition")
        self.resize(1350, 850)
        
        # 1. Khởi tạo danh sách quản lý các bộ giải mã đang hoạt động
        self.active_decoders = []
        
        # 2. Thiết lập Widget trung tâm và Layout chính
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setSpacing(10)
        
        # === KHU VỰC BÊN TRÁI: HIỂN THỊ DỮ LIỆU (80% CHIỀU RỘNG) ===
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Thành phần vẽ đồ thị
        self.plot_manager = PlotManager()
        self.left_layout.addWidget(self.plot_manager, stretch=7)
        
        # Nút kích hoạt phân tích (Dùng cho cả Mock Data và Data thật sau này)
        self.btn_run = QPushButton("RUN ANALYSIS: Capture & Decode")
        self.btn_run.setStyleSheet("""
            QPushButton {
                padding: 15px; 
                background-color: #2E7D32; 
                color: white; 
                font-weight: bold; 
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #388E3C; }
            QPushButton:pressed { background-color: #1B5E20; }
        """)
        self.btn_run.clicked.connect(self.run_analysis_flow)
        self.left_layout.addWidget(self.btn_run)
        
        # --- THÊM CODE MỚI VÀO ĐÂY ---
        self.btn_mock = QPushButton("TEST: Load Mock Data (Offline)")
        self.btn_mock.setStyleSheet("""
            QPushButton {
                padding: 10px; 
                background-color: #007ACC; 
                color: white; 
                font-weight: bold; 
                border-radius: 4px;
                margin-top: 5px;
                margin-bottom: 10px;
            }
            QPushButton:hover { background-color: #005A9E; }
        """)
        self.btn_mock.clicked.connect(self.run_mock_test)
        self.left_layout.addWidget(self.btn_mock)
        # ----------------------------
        
        # Thành phần hiển thị bảng Log
        self.transaction_log = TransactionLog()
        self.left_layout.addWidget(self.transaction_log, stretch=3)
        
        # === KHU VỰC BÊN PHẢI: ĐIỀU KHIỂN (20% CHIỀU RỘNG) ===
        self.control_panel = ControlPanel()
        # Kết nối các tín hiệu từ ControlPanel
        self.control_panel.on_decoder_added.connect(self.handle_new_decoder)
        self.control_panel.btn_clear.clicked.connect(self.clear_decoders)

        # --- KHỞI TẠO LUỒNG ĐỌC SERIAL ---
        # LƯU Ý: Bạn cần đổi '/dev/ttyACM0' thành cổng COM thực tế của bạn (VD: 'COM3' trên Windows)
        # stm32 use ACM0, esp32 use USB0
        self.serial_thread = SerialReaderThread(port='/dev/ttyUSB0', baudrate=921600)
        self.serial_thread.on_data_received.connect(self.process_real_data)
        self.serial_thread.on_status_update.connect(self.update_status_log)
        
        # Lắp ráp hai bảng vào giao diện chính
        self.main_layout.addWidget(self.left_panel, stretch=8)
        self.main_layout.addWidget(self.control_panel, stretch=2)

    # --- HÀM XỬ LÝ LOGIC ---

    def handle_new_decoder(self, config):
        """Tiếp nhận cấu hình từ giao diện và tạo đối tượng Decoder tương ứng."""
        protocol = config['protocol']
        
        try:
            if protocol == 'UART':
                new_dec = UARTDecoder(tx_channel=config['tx'], baud_rate=config['baud'])
            elif protocol == 'I2C':
                new_dec = I2CDecoder(sda_channel=config['sda'], scl_channel=config['scl'])
            elif protocol == 'SPI':
                new_dec = SPIDecoder(sck_channel=config['sck'], mosi_channel=config['mosi'])
            
            self.active_decoders.append(new_dec)
            # Sau khi thêm, tự động chạy lại phân tích để cập nhật bảng log
            self.run_analysis_flow()
            
        except Exception as e:
            print(f"Lỗi khi khởi tạo bộ giải mã: {e}")

    def clear_decoders(self):
        """Xóa sạch danh sách bộ giải mã và làm mới giao diện."""
        self.active_decoders.clear()
        self.control_panel.list_active.clear()
        self.transaction_log.update_logs([])

    def run_analysis_flow(self):
        """Thay vì tự sinh data giả, hàm này giờ sẽ ra lệnh cho SerialThread khởi động."""
        self.transaction_log.update_logs([{'time': '-', 'channel': 'SYS', 'protocol': 'INFO', 'data': 'Đang chờ ESP32...'}])
        
        # Bắt đầu luồng đọc USB (Luồng này sẽ tự động gửi chữ 'S' xuống ESP32)
        if not self.serial_thread.isRunning():
            self.serial_thread.start()

    def process_real_data(self, sample_rate, buffer_array):
        """Hàm này tự động kích hoạt khi SerialThread ném mảng numpy hoàn chỉnh về."""
        # Dừng luồng đọc lại để tránh nhận rác
        self.serial_thread.stop()
        
        # 1. Vẽ lên đồ thị
        # Tạo mảng thời gian tương ứng với buffer nhận được
        import numpy as np
        num_samples = len(buffer_array)
        t = np.arange(num_samples) / sample_rate
        
        self.plot_manager.update_data(t, buffer_array)
        
        # 2. Giải mã bằng các Decoder đang kích hoạt
        all_transactions = []
        for decoder in self.active_decoders:
            try:
                results = decoder.decode(sample_rate, buffer_array)
                all_results = results if isinstance(results, list) else []
                all_transactions.extend(all_results)
            except Exception as e:
                print(f"Lỗi giải mã: {e}")
                
        all_transactions.sort(key=lambda x: x.get('time_val', 0) if x.get('time_val') is not None else 0)
        self.transaction_log.update_logs(all_transactions)

    def update_status_log(self, msg):
        """In các thông báo trạng thái của cổng COM lên bảng Log."""
        entry = {
            'time': '-', 'channel': 'SYSTEM', 'protocol': 'SERIAL', 'data': msg
        }
        # Thêm vào dòng đầu tiên của bảng log hiện tại
        row = self.transaction_log.rowCount()
        self.transaction_log.insertRow(row)
        for col, key in enumerate(['time', 'channel', 'protocol', 'data']):
            from PyQt5.QtWidgets import QTableWidgetItem
            self.transaction_log.setItem(row, col, QTableWidgetItem(entry[key]))

    def run_mock_test(self):
        """Mô phỏng việc nhận dữ liệu hoàn chỉnh để kiểm thử UI và thuật toán."""
        self.update_status_log("Đang sinh dữ liệu mô phỏng (Mock Data)...")
        
        # Lấy dữ liệu từ file sinh giả lập
        t, buffer_array = MockDataGenerator.get_8ch_mock_data()
        sample_rate = 500000 
        
        # Bơm thẳng dữ liệu giả vào luồng xử lý chính như thể nó vừa được gửi từ STM32 lên
        self.process_real_data(sample_rate, buffer_array)