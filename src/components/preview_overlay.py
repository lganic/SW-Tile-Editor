from PySide6 import QtCore, QtGui, QtWidgets

from ..utility import darklight_from_lightcolor

class PreviewOverlay(QtWidgets.QGraphicsItem):
    """Draws live helpers: add-vertex ghost + triangle-mode previews."""
    def __init__(self, main_ref):
        super().__init__()
        self.setZValue(9999)  # above everything
        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self._main = main_ref
        self._mouse = QtCore.QPointF()

        self._helper_pen = QtGui.QPen(darklight_from_lightcolor(0, 0, 0, 160), 5)
        self._helper_pen.setCosmetic(True)

    def setMouse(self, pt: QtCore.QPointF):
        if pt == self._mouse:
            return
        self.prepareGeometryChange()
        self._mouse = pt
        self.update()

    # gigantic rect so we always get repaints when needed
    def boundingRect(self):
        return QtCore.QRectF(-1e9, -1e9, 2e9, 2e9)

    def paint(self, p, opt, w):
        m = self._main

        # Triangle-mode previews
        if m.tri_mode:
            buf = m.tri_buffer
            model = m.models[m.active_mesh]
            pts = model.points()
            p.setPen(self._helper_pen)
            p.setBrush(QtGui.QColor(0, 0, 0, 25))

            if len(buf) == 1 and buf[0] < len(pts):
                p1 = pts[buf[0]]
                p.drawLine(p1, self._mouse)

            elif len(buf) == 2 and max(buf) < len(pts):
                p1, p2 = pts[buf[0]], pts[buf[1]]
                poly = QtGui.QPolygonF([p1, p2, self._mouse])
                p.drawPolygon(poly)