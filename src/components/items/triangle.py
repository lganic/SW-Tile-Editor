from ..model import MeshModel

from PySide6 import QtGui, QtWidgets

class TriangleItem(QtWidgets.QGraphicsPathItem):
    def __init__(self, model: MeshModel, tri_index: int, color: QtGui.QColor):
        super().__init__()
        self.model = model
        self.tri_index = tri_index
        self.base_color = color

        pen_color = QtGui.QColor(color)
        pen_color = QtGui.QColor.fromHsv(pen_color.hue(), pen_color.saturation(), max(0, pen_color.value()-60))

        pen = QtGui.QPen(pen_color, 4)
        pen.setCosmetic(True)  

        self.setPen(pen)
        self.setBrush(QtGui.QBrush(QtGui.QColor(color.red(), color.green(), color.blue(), 90)))
        self.setZValue(1)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.model.changed.connect(self.rebuild_path)
        self.rebuild_path()

    def rebuild_path(self):
        tris = self.model.triangles()
        if self.tri_index >= len(tris):
            self.setPath(QtGui.QPainterPath()); return
        
        i, j, k = tris[self.tri_index]
        pts = self.model.points()
        if any(idx >= len(pts) for idx in (i, j, k)):
            self.setPath(QtGui.QPainterPath()); return
        p1, p2, p3 = pts[i], pts[j], pts[k]
        path = QtGui.QPainterPath(p1)
        path.lineTo(p2); path.lineTo(p3)
        path.closeSubpath()
        self.setPath(path)