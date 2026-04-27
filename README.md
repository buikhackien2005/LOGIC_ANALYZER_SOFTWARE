# ESP32 Logic Analyzer - Pro Edition

Một hệ thống phân tích logic (Logic Analyzer) 8 kênh hiệu năng cao, kết hợp giữa vi điều khiển ESP32 và phần mềm phân tích trên PC viết bằng Python (PyQt5). Hệ thống hỗ trợ lấy mẫu tốc độ cao 500kHz và giải mã đa giao thức (UART, I2C, SPI) theo thời gian thực.

## 🏗 Kiến trúc Hệ thống
Dự án được chia làm 2 phân hệ độc lập:
1. **PC Software (Python/PyQt5):** Quản lý giao diện, hiển thị đồ thị Waveform đa kênh, xử lý đa luồng (Threading) để đọc dữ liệu cổng COM, và vận hành hệ thống giải mã Đa hình (Polymorphism) cho các giao thức nhúng.
2. **Firmware (C/C++):** Chạy trên ESP32, sử dụng Hardware Timer Interrupt và truy xuất thanh ghi trực tiếp (Register-level access) để đảm bảo tốc độ lấy mẫu không bị trễ pha.

---

## 🔌 Yêu cầu Kỹ thuật Firmware & Hardware I/O

Phân hệ Firmware bắt buộc phải tuân thủ nghiêm ngặt các đặc tả dưới đây để đảm bảo tính toàn vẹn của phần mềm PC.

### 1. Cấu hình Input/Output
* **Điện áp giới hạn:** Các chân GPIO của ESP32 **CHỈ CHỊU ĐƯỢC TỐI ĐA 3.3V**. Bắt buộc sử dụng mạch Logic Level Shifter nếu đo tín hiệu 5V.
* **Quy hoạch chân (Pin Mapping):** Bắt buộc chọn 8 chân GPIO liền kề nhau trên cùng một thanh ghi (Ví dụ: `GPIO12` đến `GPIO19`).
* **Trạng thái chân:** Cấu hình toàn bộ 8 chân ở chế độ `INPUT`. Khuyến nghị bật `INPUT_PULLDOWN` hoặc `INPUT_PULLUP` nội bộ để chống nhiễu thả nổi.
* **Giao tiếp PC:** Sử dụng Hardware UART (Serial0) ở tốc độ **921600 bps**. Không dùng SoftwareSerial.

### 2. Yêu cầu Lấy mẫu (Sampling)
* **Tốc độ:** 500 kHz (Chu kỳ ngắt $2 \mu s$). Sử dụng Hardware Timer Interrupt.
* **Bộ đệm:** Cấp phát mảng tĩnh `uint8_t buffer[50000];` (tương đương 100ms dữ liệu).
* **Phương pháp đọc:** Bắt buộc đọc thanh ghi trạng thái GPIO bằng `REG_READ(GPIO_IN_REG)` trong 1 chu kỳ máy. Dùng phép dịch bit (Bitwise) để trích xuất 8 kênh, ép thành 1 byte và lưu vào buffer. **Tuyệt đối không dùng vòng lặp `digitalRead()`**.

### 3. Cỗ máy trạng thái (State Machine)
1. **Idle:** Đứng im lắng nghe UART.
2. **Trigger:** Kích hoạt ngắt Timer lấy mẫu chỉ khi nhận được ký tự **`'S'`** (0x53) từ PC.
3. **Blocking:** Đóng băng hệ thống trong lúc lấy 50,000 mẫu, không in log rác.
4. **Transmit:** Bắn gói dữ liệu nhị phân lên PC và quay lại bước 1.

### 4. Giao thức Khung truyền Nhị phân (Binary Packet Protocol)
Không sử dụng chuỗi ASCII (`Serial.print`). Bắt buộc dùng `Serial.write` theo cấu trúc:

| Byte | Tên trường | Giá trị | Mô tả |
| :--- | :--- | :--- | :--- |
| 1 | **SYNC 1** | `0xAA` | Dấu hiệu Start of Frame |
| 2 | **SYNC 2** | `0x55` | Xác nhận Start of Frame |
| 3 | **LENGTH (H)** | `0xC3` | Byte cao của số lượng mẫu (50000 = 0xC350) |
| 4 | **LENGTH (L)** | `0x50` | Byte thấp của số lượng mẫu |
| 5... | **PAYLOAD** | Data | Mảng 50,000 bytes trạng thái logic |
| Cuối | **CHECKSUM** | Tính toán | Phép **XOR (`^`)** toàn bộ PAYLOAD. |

---

## 💻 Hướng dẫn Cài đặt & Chạy PC Software

Phần mềm PC được phát triển trên Linux (Ubuntu) sử dụng môi trường ảo hóa để tránh xung đột thư viện hệ thống (PEP 668).

### Bước 1: Clone dự án
```bash
git clone [https://github.com/buikhackien2005/LOGIC_ANALYZER_SOFTWARE.git](https://github.com/buikhackien2005/LOGIC_ANALYZER_SOFTWARE.git)
cd logic_analyzer_pc