from PySide6 import QtCore, QtGui, QtWidgets
from ..utility import darklight_from_lightcolor

class GridBackground(QtWidgets.QGraphicsItem):
    def boundingRect(self):
        return QtCore.QRectF(-1e6, -1e6, 2e6, 2e6)

    def paint(self, p, opt, w):
        view = self.scene().views()[0] if self.scene().views() else None
        if not view: return
        rect = view.mapToScene(view.viewport().rect()).boundingRect()

        bg_color = darklight_from_lightcolor(240, 240, 240)
        p.fillRect(rect, bg_color)

        line_color = darklight_from_lightcolor(25, 25, 25)

        p.setPen(QtGui.QPen(line_color))
        step = 50
        x0 = int(rect.left())//step*step
        y0 = int(rect.top())//step*step
        for x in range(x0, int(rect.right())+step, step):
            p.drawLine(x, rect.top(), x, rect.bottom())
        for y in range(y0, int(rect.bottom())+step, step):
            p.drawLine(rect.left(), y, rect.right(), y)