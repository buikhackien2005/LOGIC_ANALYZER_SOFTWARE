import sys
from PyQt5.QtWidgets import QApplication
# Import từ các module của chúng ta
from ui.main_window import MainWindow

def main():
    # Khởi tạo Application của PyQt
    app = QApplication(sys.argv)
    
    # Khởi tạo và hiển thị Giao diện chính
    window = MainWindow()
    window.show()
    
    # Bắt đầu vòng lặp sự kiện (Event Loop)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()