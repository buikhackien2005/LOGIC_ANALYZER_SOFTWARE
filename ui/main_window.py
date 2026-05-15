from PyQt5.QtWidgets import QFileDialog, QMessageBox # Thêm thư viện hộp thoại
from utils.data_exporter import VCDExporter          # Import thuật toán xuất file bạn vừa viết
import numpy as np
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QTableWidgetItem
from ui.plot_manager import PlotManager
from ui.transaction_log import TransactionLog
from ui.control_panel import ControlPanel
from utils.mock_generator import MockDataGenerator
from core.serial_reader import SerialReaderThread

# Import an toàn các lớp giải mã từ lõi hệ thống
from core.decoders.uart_decoder import UARTDecoder

# Tránh crash phần mềm nếu bạn chưa tạo file i2c_decoder.py và spi_decoder.py
try:
    from core.decoders.i2c_decoder import I2CDecoder
except ImportError:
    I2CDecoder = None

try:
    from core.decoders.spi_decoder import SPIDecoder
except ImportError:
    SPIDecoder = None

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
        
        # === KHU VỰC BÊN TRÁI: HIỂN THỊ DỮ LIỆU ===
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.plot_manager = PlotManager()
        self.left_layout.addWidget(self.plot_manager, stretch=7)
        
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
        
        # --- THÊM CODE MỚI BƯỚC 2 VÀO ĐÂY ---
        self.btn_export = QPushButton("EXPORT: Save as .vcd (Standard)")
        self.btn_export.setStyleSheet("""
            QPushButton {
                padding: 10px; 
                background-color: #E67E22; /* Màu cam nổi bật */
                color: white; 
                font-weight: bold; 
                border-radius: 4px;
                margin-bottom: 10px;
            }
            QPushButton:hover { background-color: #D35400; }
        """)
        self.btn_export.clicked.connect(self.export_vcd_action)
        self.left_layout.addWidget(self.btn_export)
        
        # Biến lưu trữ dữ liệu tạm để chờ xuất file
        self.current_buffer = None
        self.current_sample_rate = 500000
        # ------------------------------------
        
        self.transaction_log = TransactionLog()
        self.left_layout.addWidget(self.transaction_log, stretch=3)
        
        # === KHU VỰC BÊN PHẢI: ĐIỀU KHIỂN ===
        self.control_panel = ControlPanel()
        self.control_panel.on_decoder_added.connect(self.handle_new_decoder)
        self.control_panel.btn_clear.clicked.connect(self.clear_decoders)

        # KHỞI TẠO LUỒNG ĐỌC SERIAL
        self.serial_thread = SerialReaderThread(port='/dev/ttyUSB0', baudrate=921600)
        self.serial_thread.on_data_received.connect(self.process_real_data)
        self.serial_thread.on_status_update.connect(self.update_status_log)
        
        self.main_layout.addWidget(self.left_panel, stretch=8)
        self.main_layout.addWidget(self.control_panel, stretch=2)

    # --- HÀM XỬ LÝ LOGIC ---
    def handle_new_decoder(self, config):
        """Tiếp nhận cấu hình từ giao diện và tạo đối tượng Decoder tương ứng."""
        protocol = config['protocol']
        
        try:
            new_dec = None
            if protocol == 'UART':
                new_dec = UARTDecoder(tx_channel=config['tx'], baud_rate=config['baud'])
            elif protocol == 'I2C' and I2CDecoder is not None:
                new_dec = I2CDecoder(sda_channel=config['sda'], scl_channel=config['scl'])
            elif protocol == 'SPI' and SPIDecoder is not None:
                new_dec = SPIDecoder(sck_channel=config['sck'], mosi_channel=config['mosi'])
            
            if new_dec is not None:
                self.active_decoders.append(new_dec)
                print(f"[Backend] Đã nạp thuật toán: {protocol}")
            else:
                print(f"[Cảnh báo] Lớp giải mã cho {protocol} chưa được tạo hoặc import lỗi!")
                
            # TUYỆT ĐỐI KHÔNG GỌI self.run_analysis_flow() Ở ĐÂY
            
        except Exception as e:
            print(f"Lỗi khi khởi tạo bộ giải mã: {e}")

    def clear_decoders(self):
        """Xóa sạch danh sách bộ giải mã và làm mới giao diện."""
        self.active_decoders.clear()
        self.control_panel.list_active.clear()
        self.transaction_log.update_logs([])

    def run_analysis_flow(self):
        """Ra lệnh cho SerialThread khởi động để lắng nghe phần cứng thật."""
        self.transaction_log.update_logs([{'time': '-', 'channel': 'SYS', 'protocol': 'INFO', 'data': 'Đang chờ ESP32...'}])
        if not self.serial_thread.isRunning():
            self.serial_thread.start()

    def process_real_data(self, sample_rate, buffer_array):
        """Hàm này tự động kích hoạt khi SerialThread ném mảng numpy hoàn chỉnh về (hoặc khi gọi Mock Data)."""
        self.serial_thread.stop()

        # --- THÊM 2 DÒNG NÀY ĐỂ LƯU TRỮ DỮ LIỆU CHỜ EXPORT ---
        self.current_buffer = buffer_array
        self.current_sample_rate = sample_rate
        # ----------------------------------------------------
        
        num_samples = len(buffer_array)
        t = np.arange(num_samples) / sample_rate
        self.plot_manager.update_data(t, buffer_array)
        
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
        try:
            row = self.transaction_log.rowCount()
            self.transaction_log.insertRow(row)
            for col, key in enumerate(['time', 'channel', 'protocol', 'data']):
                self.transaction_log.setItem(row, col, QTableWidgetItem(entry[key]))
        except Exception:
            pass

    def run_mock_test(self):
        """Mô phỏng việc nhận dữ liệu hoàn chỉnh để kiểm thử UI và thuật toán."""
        self.update_status_log("Đang sinh dữ liệu mô phỏng (Mock Data)...")
        
        t, buffer_array = MockDataGenerator.get_8ch_mock_data()
        sample_rate = 500000 
        
        # Bơm thẳng dữ liệu giả vào luồng xử lý chính
        self.process_real_data(sample_rate, buffer_array)

    # --- THÊM HÀM NÀY XUỐNG CUỐI FILE MAIN_WINDOW.PY ---
    def export_vcd_action(self):
        """Mở hộp thoại lưu file và gọi thuật toán xuất VCD."""
        # Kiểm tra xem đã có dữ liệu để xuất chưa
        if self.current_buffer is None or len(self.current_buffer) == 0:
            QMessageBox.warning(self, "Lỗi Export", "Chưa có dữ liệu sóng! Hãy chạy Analysis hoặc Mock Data trước.")
            return

        # Mở hộp thoại chọn nơi lưu file
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Lưu file Value Change Dump", 
            "logic_capture.vcd", # Tên file mặc định
            "VCD Files (*.vcd);;All Files (*)", 
            options=options
        )

        # Nếu người dùng đã chọn đường dẫn và bấm Save
        if file_path:
            try:
                self.update_status_log(f"Đang xuất file VCD ra: {file_path}...")
                
                # Gọi thuật toán ở Bước 1
                VCDExporter.export_to_vcd(file_path, self.current_sample_rate, self.current_buffer)
                
                self.update_status_log("Xuất file VCD thành công! Có thể mở bằng PulseView.")
                QMessageBox.information(self, "Thành công", f"Đã lưu thành công file:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể ghi file: {str(e)}")