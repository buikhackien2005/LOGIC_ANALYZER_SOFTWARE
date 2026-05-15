import numpy as np
import datetime

class VCDExporter:
    @staticmethod
    def export_to_vcd(filename, sample_rate, buffer_array):
        num_samples = len(buffer_array)
        if num_samples == 0:
            return

        time_step_ns = int((1.0 / sample_rate) * 1e9) # Tính bước thời gian bằng nano-giây

        with open(filename, 'w') as f:
            # 1. Ghi Header chuẩn IEEE
            f.write(f"$date {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} $end\n")
            f.write("$version Logic Analyzer Pro - Custom VCD Exporter $end\n")
            f.write(f"$timescale {time_step_ns} ns $end\n")
            
            # 2. Khai báo 8 kênh phần cứng (Ký hiệu từ '!' đến '(' )
            symbols = ['!', '"', '#', '$', '%', '&', "'", '(']
            f.write("$scope module LogicAnalyzer $end\n")
            for ch in range(8):
                f.write(f"$var wire 1 {symbols[ch]} CH{ch} $end\n")
            f.write("$upscope $end\n")
            f.write("$enddefinitions $end\n")
            
            # 3. Dump trạng thái ban đầu (thời điểm 0)
            f.write("#0\n")
            first_val = buffer_array[0]
            for ch in range(8):
                bit = (first_val >> ch) & 1
                f.write(f"{bit}{symbols[ch]}\n")
                
            # 4. Tìm các điểm lật trạng thái (Vector hóa)
            diffs = np.diff(buffer_array)
            change_indices = np.where(diffs != 0)[0] + 1
            
            # 5. Duyệt và ghi sự thay đổi
            prev_val = first_val
            for idx in change_indices:
                f.write(f"#{idx}\n") # Ghi mốc thời gian (nhân với time_step_ns khi phần mềm khác đọc)
                curr_val = buffer_array[idx]
                changed_bits = prev_val ^ curr_val
                
                for ch in range(8):
                    if (changed_bits >> ch) & 1: # Nếu kênh này bị thay đổi
                        bit = (curr_val >> ch) & 1
                        f.write(f"{bit}{symbols[ch]}\n")
                prev_val = curr_val