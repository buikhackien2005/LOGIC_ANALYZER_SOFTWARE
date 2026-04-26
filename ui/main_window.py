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
        
        # Thành phần hiển thị bảng Log
        self.transaction_log = TransactionLog()
        self.left_layout.addWidget(self.transaction_log, stretch=3)
        
        # === KHU VỰC BÊN PHẢI: ĐIỀU KHIỂN (20% CHIỀU RỘNG) ===
        self.control_panel = ControlPanel()
        # Kết nối các tín hiệu từ ControlPanel
        self.control_panel.on_decoder_added.connect(self.handle_new_decoder)
        self.control_panel.btn_clear.clicked.connect(self.clear_decoders)
        
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
        """
        Luồng xử lý chính: 
        Thu thập -> Vẽ sóng -> Giải mã đa hình -> Sắp xếp thời gian -> Hiển thị Log.
        """
        # 1. Thu thập dữ liệu (Hiện tại là Mock, sau này sẽ gọi SerialReader)
        t, buf = MockDataGenerator.get_8ch_mock_data()
        sample_rate = 500000 # 500 kHz theo thiết kế hiện tại
        
        # 2. Cập nhật dữ liệu lên đồ thị
        self.plot_manager.update_data(t, buf)
        
        # 3. Thực hiện giải mã thông qua tất cả các bộ giải mã đang hoạt động
        all_transactions = []
        for decoder in self.active_decoders:
            try:
                # Mỗi decoder trả về một list các dictionary
                results = decoder.decode(sample_rate, buf)
                all_results = results if isinstance(results, list) else []
                all_transactions.extend(all_results)
            except Exception as e:
                print(f"Lỗi trong quá trình giải mã {type(decoder).__name__}: {e}")
        
        # 4. Sắp xếp các giao dịch theo trình tự thời gian thực tế
        # Sử dụng 'time_val' (float) để đảm bảo độ chính xác cao hơn chuỗi văn bản
        all_transactions.sort(key=lambda x: x.get('time_val', 0) if x.get('time_val') is not None else 0)
        
        # 5. Đẩy kết quả cuối cùng ra bảng Log
        self.transaction_log.update_logs(all_transactions)