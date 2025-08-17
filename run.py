from PySide6 import QtWidgets
from src import MainWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    w = MainWindow()
    w.resize(1200, 650)
    w.show()
    app.exec()
