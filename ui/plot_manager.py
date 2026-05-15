import pyqtgraph as pg
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QLabel
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout

class PlotManager(QWidget):
    """Quản lý khu vực vẽ đồ thị Waveform cho 8 kênh."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) # Xóa viền thừa
        
        # Cấu hình UI của Plot
        pg.setConfigOption('background', '#121212')
        pg.setConfigOption('foreground', '#E0E0E0')
        self.plot_widget = pg.PlotWidget(title="Waveform Viewer (8 Channels)")
        # Khởi tạo Label hiển thị kết quả đo lường (nền đen chữ vàng cho ngầu)
        self.cursor_label = QLabel("ΔT: 0.000 ms | Freq: 0.0 Hz")
        self.cursor_label.setStyleSheet("color: #FFD700; font-weight: bold; background-color: #111; padding: 5px;")
        
        # Thêm label vào layout (bạn có thể cần tổ chức lại layout một chút)
        # layout.addWidget(self.cursor_label)

        # Tạo 2 đường thẳng đứng, màu đỏ và màu lục, cho phép kéo thả
        self.cursor_a = pg.InfiniteLine(pos=0.01, angle=90, movable=True, pen=pg.mkPen('r', width=2))
        self.cursor_b = pg.InfiniteLine(pos=0.03, angle=90, movable=True, pen=pg.mkPen('g', width=2))
        
        self.plot_widget.addItem(self.cursor_a)
        self.plot_widget.addItem(self.cursor_b)
        
        # Bắt sự kiện khi chuột kéo các đường thẳng này
        self.cursor_a.sigDragged.connect(self.update_cursor_calc)
        self.cursor_b.sigDragged.connect(self.update_cursor_calc)

        layout.addWidget(self.plot_widget)
        
        # Khởi tạo trục Y cho 8 kênh
        self.plot_widget.setYRange(-1, 16)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Cài đặt nhãn cho các kênh
        ay = self.plot_widget.getAxis('left')
        ticks = [[(i * 2 + 0.5, f"CH{i}") for i in range(8)]]
        ay.setTicks(ticks)
        
        # Bảng màu cố định cho 8 kênh
        self.colors = ['#FF5252', '#448AFF', '#69F0AE', '#FFD740', 
                       '#E040FB', '#18FFFF', '#FFAB40', '#B0BEC5']

    def update_data(self, time_array, buffer_array):
        """Hàm này nhận data nhị phân và tự động unpack để vẽ lên đồ thị."""
        self.plot_widget.clear()
        
        for ch in range(8):
            # Giải mã bitwise và offset trục Y
            ch_data = (buffer_array >> ch) & 1 
            y_render = ch_data + (ch * 2)
            
            # Vẽ đường sóng
            pen = pg.mkPen(self.colors[ch], width=1.5)
            self.plot_widget.plot(time_array, y_render, pen=pen)

    def update_cursor_calc(self):
        # Lấy tọa độ trục X (thời gian) của 2 con trỏ
        pos_a = self.cursor_a.value()
        pos_b = self.cursor_b.value()
        
        delta_t = abs(pos_a - pos_b)
        
        if delta_t == 0:
            self.cursor_label.setText("ΔT: 0.000 ms | Freq: N/A")
            return
            
        freq_hz = 1.0 / delta_t
        
        # Định dạng hiển thị linh hoạt
        if delta_t < 0.001:
            time_str = f"ΔT: {delta_t * 1000000:.2f} µs"
        else:
            time_str = f"ΔT: {delta_t * 1000:.3f} ms"
            
        if freq_hz > 1000:
            freq_str = f"Freq: {freq_hz / 1000:.2f} kHz"
        else:
            freq_str = f"Freq: {freq_hz:.1f} Hz"
            
        self.cursor_label.setText(f"{time_str}  |  {freq_str}")