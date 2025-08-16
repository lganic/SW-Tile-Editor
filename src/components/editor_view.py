from PySide6 import QtCore, QtGui, QtWidgets

class EditorView(QtWidgets.QGraphicsView):
    deletePressed = QtCore.Signal()
    sceneMouseMoved = QtCore.Signal(QtCore.QPointF)      # NEW
    sceneLeftClicked = QtCore.Signal(QtCore.QPointF)     # NEW

    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, e):
        factor = 1.15 if e.angleDelta().y() > 0 else 1/1.15
        self.scale(factor, factor)

    def keyPressEvent(self, e):
        if e.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            self.deletePressed.emit()
        else:
            super().keyPressEvent(e)

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        self.sceneMouseMoved.emit(self.mapToScene(e.position().toPoint()))

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self.sceneLeftClicked.emit(self.mapToScene(e.position().toPoint()))
        super().mousePressEvent(e)