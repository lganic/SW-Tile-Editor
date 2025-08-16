# pip install PySide6
from PySide6 import QtCore, QtGui, QtWidgets

# ------------------ Model ------------------

class MeshModel(QtCore.QObject):
    changed = QtCore.Signal()        # geometry change (move verts) or structure change (add tri/vert)

    def __init__(self):
        super().__init__()
        self._pts: list[QtCore.QPointF] = []
        self._tris: list[tuple[int, int, int]] = []

    # --- vertices ---
    def add_point(self, p: QtCore.QPointF) -> int:
        self._pts.append(QtCore.QPointF(p))
        self.changed.emit()
        return len(self._pts) - 1

    def points(self):
        return self._pts

    def set_point(self, i: int, p: QtCore.QPointF):
        self._pts[i] = QtCore.QPointF(p)
        self.changed.emit()

    # --- triangles (indices into points) ---
    def triangles(self):
        return self._tris

    def add_triangle(self, i, j, k):
        if len({i, j, k}) != 3:
            return  # ignore degenerate / duplicate selections
        # simple validation: indices in range
        n = len(self._pts)
        if any(idx < 0 or idx >= n for idx in (i, j, k)):
            return
        self._tris.append((i, j, k))
        self.changed.emit()

    def delete_last_triangle(self):
        if self._tris:
            self._tris.pop()
            self.changed.emit()


# ------------------ View Items ------------------

class VertexItem(QtCore.QObject, QtWidgets.QGraphicsEllipseItem):
    clicked = QtCore.Signal(int)
    def __init__(self, model: MeshModel, index: int, radius=6):
        QtCore.QObject.__init__(self)
        QtWidgets.QGraphicsEllipseItem.__init__(self, -radius, -radius, 2*radius, 2*radius)

        self._default_brush = QtGui.QBrush(QtGui.QColor(50, 140, 255))
        self._selected_brush = QtGui.QBrush(QtGui.QColor(255, 170, 0))
        self.setBrush(self._default_brush)

        self.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)   # ensure selectable
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


class TriangleItem(QtWidgets.QGraphicsPathItem):
    def __init__(self, model: MeshModel, tri_index: int):
        super().__init__()
        self.model = model
        self.tri_index = tri_index
        self.setPen(QtGui.QPen(QtGui.QColor(40, 40, 40), 1.5))
        self.setBrush(QtGui.QBrush(QtGui.QColor(150, 200, 255, 80)))
        self.setZValue(1)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)  # make triangles selectable
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


class EditorView(QtWidgets.QGraphicsView):
    deletePressed = QtCore.Signal()

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



class PreviewWidget(QtWidgets.QWidget):
    def __init__(self, model: MeshModel):
        super().__init__()
        self.model = model
        self.model.changed.connect(self.update)
        self.setMinimumWidth(320)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(250, 250, 250))

        pts = self.model.points()
        tris = self.model.triangles()
        if len(pts) < 3 or not tris:
            return

        # Fit all triangle geometry to widget bounds
        used_points = [pts[i] for tri in tris for i in tri]
        bounds = QtGui.QPolygonF(used_points).boundingRect()
        if bounds.width() == 0 or bounds.height() == 0:
            return

        margin = 20
        target = self.rect().adjusted(margin, margin, -margin, -margin)
        sx = target.width() / bounds.width()
        sy = target.height() / bounds.height()
        s = min(sx, sy)
        tx = target.center().x() - s*(bounds.center().x())
        ty = target.center().y() - s*(bounds.center().y())
        transform = QtGui.QTransform().scale(s, s).translate(tx/s, ty/s)

        p.setPen(QtGui.QPen(QtGui.QColor(30,30,30), 1.5))
        p.setBrush(QtGui.QColor(120, 180, 255, 120))

        for i, j, k in tris:
            try:
                poly = QtGui.QPolygonF([pts[i], pts[j], pts[k]])
            except IndexError:
                continue
            mapped = transform.map(poly)
            p.drawPolygon(mapped)




# ------------------ Main UI / Controller ------------------

class Main(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Triangle Mesh Editor")

        # Model
        self.model = MeshModel()

        # Scene & view
        self.scene = QtWidgets.QGraphicsScene()
        self.scene.addItem(GridBackground())

        self.editor = EditorView(self.scene)
        self.editor.setSceneRect(-300, -300, 800, 600)

        # Right preview
        self.preview = PreviewWidget(self.model)

        # Splitter
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        # Toolbar
        toolbar = self._make_toolbar()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(toolbar)
        layout.addWidget(splitter)

        # triangle pick state
        self.tri_mode = False
        self.tri_buffer: list[int] = []  # holds up to 3 vertex indices while creating a triangle
        self.vertex_items: list[VertexItem] = []
        self.triangle_items: list[TriangleItem] = []

        self.editor.deletePressed.connect(self.delete_selected)

        # seed with a few points
        for p in [(0,0), (200,0), (120,150), (40,120), (260,100)]:
            self._add_vertex_item(QtCore.QPointF(*p))

        for t in [(0, 1, 2)]:
            self.model.add_triangle(*t)
            self._add_triangle_item()

    # --- helpers to add items ---
    def _add_vertex_item(self, p: QtCore.QPointF):
        idx = self.model.add_point(p)
        it = VertexItem(self.model, idx)
        it.clicked.connect(self._on_vertex_clicked)
        self.scene.addItem(it)
        self.vertex_items.append(it)
        return it

    def _add_triangle_item(self):
        tri_idx = len(self.model.triangles()) - 1
        it = TriangleItem(self.model, tri_idx)
        self.scene.addItem(it)
        self.triangle_items.append(it)

    # --- selection / tri building ---
    def _on_vertex_clicked(self, idx: int):
        if not self.tri_mode:
            return
        if idx in self.tri_buffer:
            # toggle off if clicked again
            self.tri_buffer.remove(idx)
            self.vertex_items[idx].setTriPickSelected(False)
            return

        self.tri_buffer.append(idx)
        self.vertex_items[idx].setTriPickSelected(True)

        if len(self.tri_buffer) == 3:
            i, j, k = self.tri_buffer
            self.model.add_triangle(i, j, k)
            self._add_triangle_item()
            # clear visual selection
            for v_idx in self.tri_buffer:
                self.vertex_items[v_idx].setTriPickSelected(False)
            self.tri_buffer.clear()

    # --- toolbar & actions ---
    def _make_toolbar(self):
        bar = QtWidgets.QToolBar()

        add_vert = QtGui.QAction("Add Vertex", bar)
        make_tri = QtGui.QAction("Make Triangle", bar)
        make_tri.setCheckable(True)
        del_last_tri = QtGui.QAction("Delete Last Triangle", bar)
        reset_view = QtGui.QAction("Reset View", bar)

        def on_add_vertex():
            # drop at view center in scene coords
            v = next((vw for vw in self.scene.views()), None)
            if v:
                center_view = v.viewport().rect().center()
                scene_pos = v.mapToScene(center_view)
            else:
                scene_pos = QtCore.QPointF(0, 0)
            self._add_vertex_item(scene_pos)

        def on_make_tri_toggled(checked):
            self.tri_mode = checked
            # clear any partial selection when leaving mode
            if not checked:
                for v_idx in self.tri_buffer:
                    self.vertex_items[v_idx].setTriPickSelected(False)
                self.tri_buffer.clear()

        def on_delete_last_tri():
            if not self.model.triangles():
                return
            # remove last triangle item from scene
            last_item = self.triangle_items.pop() if self.triangle_items else None
            if last_item:
                self.scene.removeItem(last_item)
            self.model.delete_last_triangle()

        def on_reset_view():
            v = next((vw for vw in self.scene.views()), None)
            if v:
                v.resetTransform()
                # compute bounds of all points/triangles
                pts = self.model.points()
                if pts:
                    rect = QtGui.QPolygonF(pts).boundingRect().adjusted(-50, -50, 50, 50)
                else:
                    rect = QtCore.QRectF(-100, -100, 200, 200)
                v.fitInView(rect, QtCore.Qt.KeepAspectRatio)

        add_vert.triggered.connect(on_add_vertex)
        make_tri.toggled.connect(on_make_tri_toggled)
        del_last_tri.triggered.connect(on_delete_last_tri)
        reset_view.triggered.connect(on_reset_view)

        bar.addAction(add_vert)
        bar.addSeparator()
        bar.addAction(make_tri)
        bar.addAction(del_last_tri)
        bar.addSeparator()
        bar.addAction(reset_view)
        return bar

    def delete_selected(self):
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return

        # collect vertices and triangles to remove
        verts_to_remove = set()
        tris_to_remove = set()

        for it in selected_items:
            if isinstance(it, VertexItem):
                verts_to_remove.add(it.index)
            elif isinstance(it, TriangleItem):
                tris_to_remove.add(it.tri_index)

        # remove triangles that reference any vertex being removed
        for tri_idx, tri in enumerate(self.model.triangles()):
            if any(v in verts_to_remove for v in tri):
                tris_to_remove.add(tri_idx)

        # build new filtered vertex/triangle lists
        old_pts = self.model.points()
        old_tris = self.model.triangles()
        idx_map = {}
        new_pts = []
        for old_idx, pt in enumerate(old_pts):
            if old_idx not in verts_to_remove:
                idx_map[old_idx] = len(new_pts)
                new_pts.append(pt)

        new_tris = []
        for old_idx, tri in enumerate(old_tris):
            if old_idx not in tris_to_remove:
                try:
                    new_tris.append(tuple(idx_map[v] for v in tri))
                except KeyError:
                    pass  # vertex missing, skip

        # update model
        self.model._pts = new_pts
        self.model._tris = new_tris

        # rebuild scene
        self._rebuild_scene()

    def _rebuild_scene(self):
        self.scene.clear()
        self.scene.addItem(GridBackground())
        self.vertex_items.clear()
        self.triangle_items.clear()

        for tri_idx, _ in enumerate(self.model.triangles()):
            tri_item = TriangleItem(self.model, tri_idx)
            self.scene.addItem(tri_item)
            self.triangle_items.append(tri_item)

        for idx, pt in enumerate(self.model.points()):
            v_item = VertexItem(self.model, idx)
            v_item.clicked.connect(self._on_vertex_clicked)
            self.scene.addItem(v_item)
            self.vertex_items.append(v_item)


# ------------------ main ------------------

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    w = Main()
    w.resize(1100, 600)
    w.show()
    app.exec()
