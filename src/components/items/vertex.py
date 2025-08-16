from ..model import MeshModel

from PySide6 import QtCore, QtGui, QtWidgets

class VertexItem(QtCore.QObject, QtWidgets.QGraphicsEllipseItem):
    clicked = QtCore.Signal(int)

    def __init__(self, model: MeshModel, index: int, color: QtGui.QColor, radius=6):
        QtCore.QObject.__init__(self)
        QtWidgets.QGraphicsEllipseItem.__init__(self, -radius, -radius, 2*radius, 2*radius)

        self._default_brush = QtGui.QBrush(color)
        # slightly warmer highlight
        sel = QtGui.QColor(color)
        sel = QtGui.QColor.fromHsv(sel.hue(), max(0, sel.saturation()-60), min(255, sel.value()+40))
        self._selected_brush = QtGui.QBrush(sel)

        # keep size constant in screen pixels
        self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations, True)

        # keep outline width constant too
        pen = QtGui.QPen(QtCore.Qt.black, 1)
        pen.setCosmetic(True)
        self.setPen(pen)

        self.setBrush(self._default_brush)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setZValue(10)

        self.model = model
        self.index = index
        self.setPos(model.points()[index])

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            self.model.set_point(self.index, value)
        return super().itemChange(change, value)

    def setTriPickSelected(self, on: bool):
        self.setBrush(self._selected_brush if on else self._default_brush)

    def mousePressEvent(self, e: QtWidgets.QGraphicsSceneMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(e)
