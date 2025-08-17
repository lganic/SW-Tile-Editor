from PySide6 import QtWidgets, QtGui
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
        exit_action = QtGui.QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(new_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        # Example Options menu
        options_menu = menubar.addMenu("Options")
        pref_action = QtGui.QAction("Preferences", self)
        options_menu.addAction(pref_action)

        new_action.triggered.connect(self._on_new_action)
    
    def _on_new_action(self):
        print("new action")


