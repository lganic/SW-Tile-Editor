from PySide6 import QtCore, QtGui, QtWidgets

class GridBackground(QtWidgets.QGraphicsItem):
    def boundingRect(self):
        return QtCore.QRectF(-1e6, -1e6, 2e6, 2e6)

    def paint(self, p, opt, w):
        view = self.scene().views()[0] if self.scene().views() else None
        if not view: return
        rect = view.mapToScene(view.viewport().rect()).boundingRect()
        p.setPen(QtGui.QPen(QtGui.QColor(230,230,230)))
        step = 50
        x0 = int(rect.left())//step*step
        y0 = int(rect.top())//step*step
        for x in range(x0, int(rect.right())+step, step):
            p.drawLine(x, rect.top(), x, rect.bottom())
        for y in range(y0, int(rect.bottom())+step, step):
            p.drawLine(rect.left(), y, rect.right(), y)