import numpy as np
from .base_decoder import ProtocolDecoder

class UARTDecoder(ProtocolDecoder):
    def __init__(self, tx_channel, baud_rate=9600):
        self.tx_channel = tx_channel
        self.baud_rate = baud_rate

    def decode(self, sample_rate, buffer_array):
        transactions = []
        spb = float(sample_rate) / self.baud_rate
        
        # 1. Trích xuất riêng kênh TX
        tx_data = (buffer_array >> self.tx_channel) & 1
        
        # 2. Tìm sườn xuống (Start bit candidate)
        falling_edges = np.where(np.diff(tx_data) == -1)[0]
        
        skip_until = 0
        for edge_idx in falling_edges:
            if edge_idx < skip_until:
                continue
                
            if edge_idx + int(spb * 10) >= len(tx_data):
                break 

            center_start_idx = int(edge_idx + spb / 2)
            if tx_data[center_start_idx] != 0:
                continue 

            byte_value = 0
            for bit_pos in range(8):
                sample_idx = int(edge_idx + (spb / 2) + ((bit_pos + 1) * spb))
                byte_value |= (tx_data[sample_idx] << bit_pos)

            stop_idx = int(edge_idx + (spb / 2) + (9 * spb))
            if tx_data[stop_idx] == 1:
                # --- ĐÓNG GÓI CHUẨN ĐẦU RA CHO UI ---
                time_sec = edge_idx / sample_rate
                char_val = chr(byte_value) if 32 <= byte_value <= 126 else '?'
                data_str = f"0x{byte_value:02X} ('{char_val}')"
                
                transactions.append({
                    'time': f"{time_sec:.5f}s",
                    'protocol': 'UART',
                    'channel': f"CH{self.tx_channel}",
                    'data': data_str
                })
            
            skip_until = edge_idx + int(spb * 10)

        return transactions