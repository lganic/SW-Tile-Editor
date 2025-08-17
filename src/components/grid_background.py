from PySide6 import QtCore, QtGui, QtWidgets
from ..utility import darklight_from_lightcolor

class GridBackground(QtWidgets.QGraphicsItem):

    def __init__(self, line_spacing):
        super().__init__()

        self.line_spacing = line_spacing

    def boundingRect(self):
        return QtCore.QRectF(-1e6, -1e6, 2e6, 2e6)

    def paint(self, p, opt, w):
        view = self.scene().views()[0] if self.scene().views() else None
        if not view: return
        rect = view.mapToScene(view.viewport().rect()).boundingRect()

        bg_color = darklight_from_lightcolor(240, 240, 240)
        p.fillRect(rect, bg_color)

        if self.line_spacing < 1:
            return # Lines too dense. Probably gonna look like shit anyway.

        step = self.line_spacing

        line_color = darklight_from_lightcolor(100, 100, 100)

        line_pen = QtGui.QPen(line_color)
        line_pen.setCosmetic(True)

        p.setPen(line_pen)
        x0 = int(rect.left())//step*step
        y0 = int(rect.top())//step*step
        for x in range(x0, int(rect.right())+step, step):
            p.drawLine(x, rect.top(), x, rect.bottom())
        for y in range(y0, int(rect.bottom())+step, step):
            p.drawLine(rect.left(), y, rect.right(), y)