import numpy as np
from .base_decoder import ProtocolDecoder

class I2CDecoder(ProtocolDecoder):
    def __init__(self, sda_channel, scl_channel):
        self.sda_channel = sda_channel
        self.scl_channel = scl_channel

    def decode(self, sample_rate, buffer_array):
        transactions = []
        
        # 1. Trích xuất cả 2 kênh
        sda = (buffer_array >> self.sda_channel) & 1
        scl = (buffer_array >> self.scl_channel) & 1
        
        # 2. TÌM START CONDITION (Cốt lõi của I2C)
        # SDA sườn xuống (diff == -1)
        sda_diff = np.diff(sda)
        sda_falling_edges = np.where(sda_diff == -1)[0]
        
        # Lọc ra những sườn xuống của SDA mà tại đó SCL đang MỨC CAO (== 1)
        start_conditions = sda_falling_edges[scl[sda_falling_edges] == 1]
        
        for start_idx in start_conditions:
            # Tạm thời chỉ xuất log báo hiệu tìm thấy mốc Start
            # (Logic đọc 8 bit theo sườn lên của SCL sẽ được phát triển tiếp)
            time_sec = start_idx / sample_rate
            transactions.append({
                'time': f"{time_sec:.5f}s",
                'protocol': 'I2C',
                'channel': f"SDA:CH{self.sda_channel}|SCL:CH{self.scl_channel}",
                'data': "[START Condition]"
            })
            
        return transactions