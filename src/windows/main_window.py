from PySide6 import QtWidgets, QtGui, QtCore
from src import Main

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SW Mesh Editor (WIP)")

        self.main_widget = Main()
        self.setCentralWidget(self.main_widget)

        # Create the menu bar
        menubar = self.menuBar()

        # Example File menu
        file_menu = menubar.addMenu("File")
        new_action = QtGui.QAction("New", self)
        open_action = QtGui.QAction("Open", self)
        exit_action = QtGui.QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(new_action)
        file_menu.addSeparator()
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        new_action.setShortcut("Ctrl+N")
        open_action.setShortcut("Ctrl+O")
        exit_action.setShortcut("Ctrl+Q")

        # Example Options menu
        options_menu = menubar.addMenu("Options")
        pref_action = QtGui.QAction("Preferences", self)
        options_menu.addAction(pref_action)

        new_action.triggered.connect(self._on_new_action)
        open_action.triggered.connect(self._on_open_action)

        self._last_dir = ""
    
    def _on_new_action(self):
        print("new action")

    def _on_open_action(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open BIN file",
            self._last_dir or "",
            "Binary Files (*.bin);;All Files (*)"
        )
        if not path:
            return
        self._last_dir = QtCore.QFileInfo(path).absolutePath() if hasattr(QtCore, "QFileInfo") else ""
        try:
            self.main_widget.open_bin_file(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Open Error", f"Failed to open file:\n{e}")