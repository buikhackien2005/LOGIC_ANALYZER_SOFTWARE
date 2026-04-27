import serial
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
import time

class SerialReaderThread(QThread):
    # Tín hiệu phát ra khi nhận đủ 1 gói dữ liệu hoàn chỉnh và hợp lệ
    # Trả về: (sample_rate, mảng_numpy_dữ_liệu)
    on_data_received = pyqtSignal(int, np.ndarray)
    
    # Tín hiệu phát ra để báo lỗi hoặc trạng thái lên UI
    on_status_update = pyqtSignal(str)

    def __init__(self, port, baudrate=921600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.is_running = False
        self.serial_port = None
        
        # Buffer để chứa các mảnh dữ liệu xé lẻ từ USB
        self.raw_buffer = bytearray()
        
        # Tốc độ lấy mẫu mặc định (Sẽ đồng bộ với Firmware sau)
        self.sample_rate = 500000 

    def run(self):
        """Hàm này tự động chạy trong 1 luồng (thread) riêng biệt khi gọi start()"""
        try:
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=0.1)
            self.is_running = True
            self.on_status_update.emit(f"Đã kết nối {self.port} @ {self.baudrate}bps")
            
            # Gửi lệnh 'S' (Start) xuống ESP32 để kích hoạt việc lấy mẫu
            self.serial_port.write(b'S')
            
        except serial.SerialException as e:
            self.on_status_update.emit(f"Lỗi mở cổng COM: {e}")
            return

        # --- CỖ MÁY TRẠNG THÁI (STATE MACHINE) ---
        STATE_WAIT_HEADER = 0
        STATE_READ_PAYLOAD = 1
        current_state = STATE_WAIT_HEADER
        expected_length = 0

        while self.is_running:
            if self.serial_port.in_waiting > 0:
                # Đọc TẤT CẢ những gì đang có ở cổng USB cất vào buffer
                chunk = self.serial_port.read(self.serial_port.in_waiting)
                self.raw_buffer.extend(chunk)

            if current_state == STATE_WAIT_HEADER:
                # Tìm chuỗi Header 0xAA 0x55
                sync_idx = self.raw_buffer.find(b'\xAA\x55')
                
                if sync_idx != -1:
                    # Đã thấy Header, cắt bỏ các byte rác phía trước
                    self.raw_buffer = self.raw_buffer[sync_idx:]
                    
                    # Kiểm tra xem đã nhận đủ 4 byte đầu tiên chưa (2 byte Sync + 2 byte Length)
                    if len(self.raw_buffer) >= 4:
                        # Tính toán độ dài Payload (Byte cao dịch trái 8 bit OR với Byte thấp)
                        len_high = self.raw_buffer[2]
                        len_low = self.raw_buffer[3]
                        expected_length = (len_high << 8) | len_low
                        
                        current_state = STATE_READ_PAYLOAD
                else:
                    # Nếu buffer quá lớn mà không thấy header, xóa bớt để chống tràn RAM
                    if len(self.raw_buffer) > 100000:
                        self.raw_buffer.clear()

            elif current_state == STATE_READ_PAYLOAD:
                # Tính tổng chiều dài khung truyền: 4 byte đầu + độ dài payload + 1 byte checksum
                total_frame_size = 4 + expected_length + 1
                
                if len(self.raw_buffer) >= total_frame_size:
                    # Đã gom đủ 1 gói tin hoàn chỉnh!
                    frame = self.raw_buffer[:total_frame_size]
                    
                    # Cắt phần đã xử lý ra khỏi buffer (để dành phần dư cho gói tin tiếp theo)
                    self.raw_buffer = self.raw_buffer[total_frame_size:]
                    
                    # Trích xuất Payload và Checksum
                    payload = frame[4 : 4 + expected_length]
                    received_checksum = frame[-1]
                    
                    # Kiểm tra Checksum bằng thuật toán XOR
                    calculated_checksum = 0
                    for byte in payload:
                        calculated_checksum ^= byte
                        
                    if calculated_checksum == received_checksum:
                        self.on_status_update.emit(f"Nhận thành công {expected_length} bytes!")
                        # Chuyển payload thành mảng NumPy uint8 và bắn tín hiệu sang UI để vẽ
                        np_data = np.frombuffer(payload, dtype=np.uint8)
                        self.on_data_received.emit(self.sample_rate, np_data)
                    else:
                        self.on_status_update.emit("Lỗi Checksum! Bỏ qua gói tin.")
                    
                    # Quay lại trạng thái chờ Header mới
                    current_state = STATE_WAIT_HEADER
            
            # Nghỉ 1ms để không ăn hết 100% CPU của luồng này
            time.sleep(0.001)

    def stop(self):
        """Dừng luồng và đóng cổng COM an toàn"""
        self.is_running = False
        self.wait() # Chờ luồng thoát hẳn vòng lặp while
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.on_status_update.emit("Đã ngắt kết nối.")