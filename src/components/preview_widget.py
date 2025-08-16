from PySide6 import QtCore, QtGui, QtWidgets

from model import MeshModel

class PreviewWidget(QtWidgets.QWidget):
    def __init__(self, models: list[MeshModel], colors: list[QtGui.QColor]):
        super().__init__()
        self.models = models
        self.colors = colors
        for m in self.models:
            m.changed.connect(self.update)
        self.setMinimumWidth(320)

        self.reset_view()
        # Pan interaction
        self._panning = False
        self._last_pos = QtCore.QPoint()

        # Smooth edges
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, True)

    def reset_view(self):
        # "Camera" state
        self._init_rect = QtCore.QRectF(-500, -500, 1000, 1000)  # requested start bounds
        self._center = QtCore.QPointF(self._init_rect.center())  # world center
        self._zoom = 1.0                                         # pixels per world unit
        self._view_inited = False


    # --------- Interaction (pan + zoom) ---------
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self._panning = True
            self._last_pos = e.pos()
            self.setCursor(QtCore.Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self._panning:
            delta_px = e.pos() - self._last_pos
            self._last_pos = e.pos()
            # pixel delta -> world delta
            if self._zoom != 0:
                self._center -= QtCore.QPointF(delta_px.x()/self._zoom, delta_px.y()/self._zoom)
                self.update()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self._panning = False
            self.setCursor(QtCore.Qt.ArrowCursor)

    def wheelEvent(self, e: QtGui.QWheelEvent):
        if e.angleDelta().y() == 0:
            return
        factor = 1.15 if e.angleDelta().y() > 0 else 1/1.15
        mouse_w = self._widget_to_world(e.position())

        # clamp zoom so it never hits zero/NaN
        self._zoom = max(1e-6, min(1e6, self._zoom * factor))

        self._recenter_to_anchor(mouse_w, e.position())
        self.update()

    def resizeEvent(self, e: QtGui.QResizeEvent):
        # re-fit initial rect on the very first layout pass
        if not self._view_inited and self.width() > 0 and self.height() > 0:
            self._center = self._init_rect.center()
            target = self._target_rect()
            if target.width() > 0 and target.height() > 0:
                self._zoom = min(target.width()/self._init_rect.width(),
                                 target.height()/self._init_rect.height())
            self._view_inited = True
        super().resizeEvent(e)

    # --------- Helpers for mapping ---------
    def _target_rect(self):
        margin = 20
        return self.rect().adjusted(margin, margin, -margin, -margin)

    def _world_rect_visible(self):
        """World rect currently visible inside target area, from center/zoom."""
        tr = self._target_rect()
        if self._zoom <= 0 or tr.isEmpty():
            return QtCore.QRectF()
        w = tr.width()  / self._zoom
        h = tr.height() / self._zoom
        return QtCore.QRectF(self._center.x() - w/2, self._center.y() - h/2, w, h)

    def _world_to_device_transform(self):
        """QTransform mapping world -> widget pixels."""
        tr = self._target_rect()
        # translate to target center, scale, then translate by -center
        T = QtGui.QTransform()
        T.translate(tr.center().x(), tr.center().y())
        T.scale(self._zoom, self._zoom)
        T.translate(-self._center.x(), -self._center.y())
        return T

    def _widget_to_world(self, pt: QtCore.QPointF) -> QtCore.QPointF:
        T = self._world_to_device_transform()
        inv, ok = T.inverted()          # <-- correct order
        return inv.map(pt) if ok else QtCore.QPointF()

    def _recenter_to_anchor(self, world_anchor: QtCore.QPointF, widget_pt: QtCore.QPointF):
        """After zoom changes, shift center so that world_anchor stays under widget_pt."""
        tr = self._target_rect()
        if tr.isEmpty() or self._zoom <= 0:
            return
        # fraction across the target rect (0..1)
        ax = (widget_pt.x() - tr.left()) / tr.width()
        ay = (widget_pt.y() - tr.top())  / tr.height()
        w = tr.width()  / self._zoom
        h = tr.height() / self._zoom
        # center such that anchor maps back to widget_pt
        self._center = QtCore.QPointF(
            world_anchor.x() + (0.5 - ax) * w,
            world_anchor.y() + (0.5 - ay) * h
        )

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(250, 250, 250))

        # draw frame for target area
        tr = self._target_rect()
        p.setPen(QtGui.QPen(QtGui.QColor(220,220,220)))
        p.drawRect(tr)

        if tr.isEmpty():
            return
        
        # world -> device transform
        T = self._world_to_device_transform()

        p.setPen(QtGui.QPen(QtGui.QColor("red"), 2, QtCore.Qt.DashLine))
        p.setBrush(QtGui.QColor(40, 100, 110))
        border_poly = QtGui.QPolygonF([
            QtCore.QPointF(-500, -500),
            QtCore.QPointF(500, -500),
            QtCore.QPointF(500, 500),
            QtCore.QPointF(-500, 500)
        ])
        mapped_border = T.map(border_poly)
        p.drawPolygon(mapped_border)

        # draw all meshes in their colors
        for mi, m in enumerate(self.models):
            tris = m.triangles()
            pts  = m.points()
            if not tris or not pts:
                continue
            pen_color = QtGui.QColor(self.colors[mi])
            brush = QtGui.QColor(self.colors[mi].red(), self.colors[mi].green(), self.colors[mi].blue())

            p.setPen(QtGui.QPen(pen_color, 1.5))
            p.setBrush(brush)

            for i, j, k in tris:
                if max(i, j, k) >= len(pts): 
                    continue
                poly = QtGui.QPolygonF([pts[i], pts[j], pts[k]])
                mapped = T.map(poly)
                p.drawPolygon(mapped)