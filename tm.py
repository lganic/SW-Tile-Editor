# pip install PySide6
from PySide6 import QtCore, QtGui, QtWidgets

from sw_ducky import MapGeometry

# ------------ Model ------------

class MeshModel(QtCore.QObject):
    changed = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._pts: list[QtCore.QPointF] = []
        self._tris: list[tuple[int, int, int]] = []

    # vertices
    def add_point(self, p: QtCore.QPointF) -> int:
        self._pts.append(QtCore.QPointF(p))
        self.changed.emit()
        return len(self._pts) - 1

    def points(self):
        return self._pts

    def set_point(self, i: int, p: QtCore.QPointF):
        self._pts[i] = QtCore.QPointF(p)
        self.changed.emit()

    # triangles (indices into points)
    def triangles(self):
        return self._tris

    def add_triangle(self, i, j, k):
        if len({i, j, k}) != 3:
            return
        n = len(self._pts)
        if any(idx < 0 or idx >= n for idx in (i, j, k)):
            return
        self._tris.append((i, j, k))
        self.changed.emit()

    def delete_last_triangle(self):
        if self._tris:
            self._tris.pop()
            self.changed.emit()


# ------------ View Items ------------

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


class PreviewOverlay(QtWidgets.QGraphicsItem):
    """Draws live helpers: add-vertex ghost + triangle-mode previews."""
    def __init__(self, main_ref):
        super().__init__()
        self.setZValue(9999)  # above everything
        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self._main = main_ref
        self._mouse = QtCore.QPointF()

        # reusable pens/brush
        self._helper_pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 160), 5)
        self._helper_pen.setCosmetic(True)
        self._ghost_pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 180), 5)
        self._ghost_pen.setCosmetic(True)
        self._ghost_br = QtGui.QBrush(QtGui.QColor(0, 0, 0, 30))

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
        # 1) Add-vertex ghost
        if m.adding_vertex:
            r = 6
            p.setPen(self._ghost_pen)
            p.setBrush(self._ghost_br)
            p.drawEllipse(self._mouse, r, r)

        # 2) Triangle-mode previews
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


# ------------ Main UI / Controller ------------

class Main(QtWidgets.QWidget):
    COLORS = [
        QtGui.QColor('#327986'), QtGui.QColor('#3D8E9F'), QtGui.QColor('#48A3B8'),
        QtGui.QColor('#53B9D1'), QtGui.QColor('#D0D0C6'), QtGui.QColor('#A4B875'),
        QtGui.QColor('#E3D08D'), QtGui.QColor('#53B9D1'), QtGui.QColor('#FFFFFF'),
        QtGui.QColor('#8B6E5C'), QtGui.QColor('#583E2D'),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Triangle Mesh Editor (11 meshes)")

        # 11 models
        self.models: list[MeshModel] = [MeshModel() for _ in range(11)]
        self.active_mesh = 0

        # Scene & view
        self.scene = QtWidgets.QGraphicsScene()
        self.scene.addItem(GridBackground())

        self.overlay = PreviewOverlay(self)
        self.scene.addItem(self.overlay)

        self.ghost_item = QtWidgets.QGraphicsEllipseItem(-6, -6, 12, 12)
        ghost_pen = QtGui.QPen(QtGui.QColor(20, 20, 20, 180), 1)
        ghost_pen.setCosmetic(True)
        self.ghost_item.setPen(ghost_pen)
        self.ghost_item.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 30)))
        self.ghost_item.setZValue(9998)
        self.ghost_item.setVisible(False)
        self.ghost_item.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations, True)  # stays constant size
        self.scene.addItem(self.ghost_item)

        self.adding_vertex = False

        # re-add border
        self.border_item = QtWidgets.QGraphicsRectItem(-500, -500, 1000, 1000)
        pen = QtGui.QPen(QtGui.QColor("red"), 2, QtCore.Qt.DashLine)
        pen.setCosmetic(True)
        self.border_item.setPen(pen)
        self.border_item.setZValue(0.5)
        self.border_item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        self.border_item.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.scene.addItem(self.border_item)

        self.editor = EditorView(self.scene)
        self.editor.setSceneRect(-300, -300, 800, 600)

        self.editor.sceneMouseMoved.connect(self._on_scene_mouse_moved)   # NEW
        self.editor.sceneLeftClicked.connect(self._on_scene_left_clicked) # NEW

        # Right preview shows all meshes
        self.preview = PreviewWidget(self.models, self.COLORS)

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

        # tri-pick state (per active mesh)
        self.tri_mode = False
        self.tri_buffer: list[int] = []  # indices within active mesh

        # Per-mesh item containers
        self.mesh_vertex_items: list[list[VertexItem]] = [[] for _ in range(11)]
        self.mesh_triangle_items: list[list[TriangleItem]] = [[] for _ in range(11)]

        self.editor.deletePressed.connect(self.delete_selected)

        LAYER_RENDER_ORDER = ['Sea-0', 'Sea-1', 'Sea-2','Sea-3', 'Land', 'Grass', 'Sand', 'Shallows', 'Snow', 'Gravel', 'Rock']

        map_geo = MapGeometry.from_file('arid.bin')

        for index, key in enumerate(LAYER_RENDER_ORDER):

            for x, y in map_geo.terrain_vertices[key]:
                self._add_vertex_item(index, QtCore.QPointF(x, y))
            
            for t in map_geo.terrain_tris[key]:
                self.models[index].add_triangle(*t)
                self._add_triangle_item(index)

        # # Seed mesh 0 with a few points and one triangle
        # for p in [(0,0), (200,0), (120,150), (40,120), (260,100)]:
        #     self._add_vertex_item(self.active_mesh, QtCore.QPointF(*p))
        # self.models[0].add_triangle(0, 1, 2)
        # self._add_triangle_item(0)

        # ensure interactivity states reflect active mesh
        self._apply_active_mesh_flags()

    # ---- helpers to add items ----
    def _add_vertex_item(self, mesh_idx: int, p: QtCore.QPointF):
        idx = self.models[mesh_idx].add_point(p)
        color = self.COLORS[mesh_idx]
        it = VertexItem(self.models[mesh_idx], idx, color)
        it.clicked.connect(lambda i, m=mesh_idx: self._on_vertex_clicked(m, i))
        self.scene.addItem(it)
        self.mesh_vertex_items[mesh_idx].append(it)
        return it

    def _add_triangle_item(self, mesh_idx: int):
        tri_idx = len(self.models[mesh_idx].triangles()) - 1
        it = TriangleItem(self.models[mesh_idx], tri_idx, self.COLORS[mesh_idx])
        self.scene.addItem(it)
        self.mesh_triangle_items[mesh_idx].append(it)

    # ---- selection / tri building ----
    def _on_vertex_clicked(self, mesh_idx: int, idx: int):
        if not self.tri_mode or mesh_idx != self.active_mesh:
            return
        if idx in self.tri_buffer:
            self.tri_buffer.remove(idx)
            self.mesh_vertex_items[mesh_idx][idx].setTriPickSelected(False)
            return

        self.tri_buffer.append(idx)
        self.mesh_vertex_items[mesh_idx][idx].setTriPickSelected(True)

        if len(self.tri_buffer) == 3:
            i, j, k = self.tri_buffer
            self.models[mesh_idx].add_triangle(i, j, k)
            self._add_triangle_item(mesh_idx)
            for v_idx in self.tri_buffer:
                self.mesh_vertex_items[mesh_idx][v_idx].setTriPickSelected(False)
            self.tri_buffer.clear()

    # ---- toolbar & actions ----
    def _make_toolbar(self):
        bar = QtWidgets.QToolBar()

        self.mesh_combo = QtWidgets.QComboBox()
        for i in range(11):
            self.mesh_combo.addItem(['Sea-0', 'Sea-1', 'Sea-2','Sea-3', 'Land', 'Grass', 'Sand', 'Shallows', 'Snow', 'Gravel', 'Rock'][i])
        self.mesh_combo.currentIndexChanged.connect(self._on_mesh_changed)
        bar.addWidget(QtWidgets.QLabel(" Active: "))
        bar.addWidget(self.mesh_combo)
        bar.addSeparator()

        add_vert = QtGui.QAction("Add Vertex", bar)
        add_vert.setCheckable(True)                                     # NEW

        make_tri = QtGui.QAction("Make Triangle", bar)
        make_tri.setCheckable(True)
        del_last_tri = QtGui.QAction("Delete Last Triangle", bar)
        reset_view = QtGui.QAction("Reset View", bar)

        # --- handlers ---
        def on_add_vertex_toggled(checked):                             # NEW
            self.adding_vertex = checked
            self.ghost_item.setVisible(checked)
            # avoid rubberband when placing a vertex
            self.editor.setDragMode(QtWidgets.QGraphicsView.NoDrag if checked
                                    else QtWidgets.QGraphicsView.RubberBandDrag)
            # normal cursor vs plus-like cursor
            self.editor.setCursor(QtCore.Qt.CrossCursor if checked else QtCore.Qt.ArrowCursor)

        def on_make_tri_toggled(checked):
            self.tri_mode = checked
            if not checked:
                for v_idx in self.tri_buffer:
                    if v_idx < len(self.mesh_vertex_items[self.active_mesh]):
                        self.mesh_vertex_items[self.active_mesh][v_idx].setTriPickSelected(False)
                self.tri_buffer.clear()
            self._update_triangle_cursor(checked)                        # NEW
            self.overlay.update()                                        # ensure preview clears

        def on_delete_last_tri():
            if not self.models[self.active_mesh].triangles():
                return
            lst = self.mesh_triangle_items[self.active_mesh]
            last_item = lst.pop() if lst else None
            if last_item:
                self.scene.removeItem(last_item)
            self.models[self.active_mesh].delete_last_triangle()

        def on_reset_view():
            v = next((vw for vw in self.scene.views()), None)
            if v:
                rect = QtCore.QRect(-500, -500, 1000, 1000)
                v.resetTransform()
                v.fitInView(rect, QtCore.Qt.KeepAspectRatio)
            self.preview.reset_view()
            self.preview.update()

        add_vert.toggled.connect(on_add_vertex_toggled)                  # NEW
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


    def _on_mesh_changed(self, idx: int):
        if idx == self.active_mesh:  # no-op
            return
        # clear any partial tri selection from previous mesh
        for v_idx in self.tri_buffer:
            if v_idx < len(self.mesh_vertex_items[self.active_mesh]):
                self.mesh_vertex_items[self.active_mesh][v_idx].setTriPickSelected(False)
        self.tri_buffer.clear()

        self.active_mesh = idx
        self._apply_active_mesh_flags()

    def _apply_active_mesh_flags(self):
        # Active mesh items: movable/selectable; others: view-only
        for mi in range(11):
            active = (mi == self.active_mesh)
            for it in self.mesh_vertex_items[mi]:
                it.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, active)
                it.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, active)
                it.setOpacity(1.0 if active else 0.1)
            for it in self.mesh_triangle_items[mi]:
                it.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, active)
                it.setOpacity(1.0 if active else 0.1)

    def delete_selected(self):
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return

        # Collect removals per model
        verts_to_remove: dict[MeshModel, set[int]] = {}
        tris_to_remove:  dict[MeshModel, set[int]] = {}

        def ensure(d, m): d.setdefault(m, set())

        for it in selected_items:
            if isinstance(it, VertexItem):
                ensure(verts_to_remove, it.model); verts_to_remove[it.model].add(it.index)
            elif isinstance(it, TriangleItem):
                ensure(tris_to_remove, it.model);  tris_to_remove[it.model].add(it.tri_index)

        # also remove any triangles referencing removed vertices
        for m in self.models:
            if m not in verts_to_remove: continue
            vset = verts_to_remove[m]
            for tri_idx, tri in enumerate(m.triangles()):
                if any(v in vset for v in tri):
                    ensure(tris_to_remove, m); tris_to_remove[m].add(tri_idx)

        # Rebuild each affected model, then rebuild scene (all meshes, simpler & safe)
        for m in set(list(verts_to_remove.keys()) + list(tris_to_remove.keys())):
            old_pts = m.points()
            old_tris = m.triangles()
            vset = verts_to_remove.get(m, set())
            tset = tris_to_remove.get(m, set())

            idx_map = {}
            new_pts = []
            for old_idx, pt in enumerate(old_pts):
                if old_idx not in vset:
                    idx_map[old_idx] = len(new_pts)
                    new_pts.append(pt)

            new_tris = []
            for old_idx, tri in enumerate(old_tris):
                if old_idx in tset: continue
                try:
                    new_tris.append(tuple(idx_map[v] for v in tri))
                except KeyError:
                    pass

            m._pts = new_pts
            m._tris = new_tris
            m.changed.emit()

        self._rebuild_scene_all()

    def _rebuild_scene_all(self):
        self.scene.clear()
        self.scene.addItem(GridBackground())
        for lst in self.mesh_vertex_items: lst.clear()
        for lst in self.mesh_triangle_items: lst.clear()

        # triangles then verts ...
        for mi, m in enumerate(self.models):
            for tri_idx, _ in enumerate(m.triangles()):
                tri_item = TriangleItem(m, tri_idx, self.COLORS[mi])
                self.scene.addItem(tri_item)
                self.mesh_triangle_items[mi].append(tri_item)

        for mi, m in enumerate(self.models):
            color = self.COLORS[mi]
            for idx, pt in enumerate(m.points()):
                v_item = VertexItem(m, idx, color)
                v_item.clicked.connect(lambda i, mesh_i=mi: self._on_vertex_clicked(mesh_i, i))
                self.scene.addItem(v_item)
                self.mesh_vertex_items[mi].append(v_item)

        border_rect = QtWidgets.QGraphicsRectItem(-500, -500, 1000, 1000)
        border_rect.setPen(QtGui.QPen(QtGui.QColor("red"), 2, QtCore.Qt.DashLine))
        border_rect.setZValue(100)
        self.scene.addItem(border_rect)
        self.border_item = border_rect

        # re-add helper items (overlay above all; ghost below it)
        self.scene.addItem(self.overlay)
        self.scene.addItem(self.ghost_item)

        self._apply_active_mesh_flags()


    def _on_scene_mouse_moved(self, scene_pt: QtCore.QPointF):
        # Move overlay & ghost
        self.overlay.setMouse(scene_pt)
        if self.adding_vertex:
            self.ghost_item.setPos(scene_pt)

    def _on_scene_left_clicked(self, scene_pt: QtCore.QPointF):
        # In add-vertex mode, drop a vertex here
        if self.adding_vertex:
            self._add_vertex_item(self.active_mesh, scene_pt)

    def _update_triangle_cursor(self, on: bool):
        if not on:
            # if leaving tri mode and not adding vertex, go back to default
            self.editor.setCursor(QtCore.Qt.ArrowCursor if not self.adding_vertex else QtCore.Qt.CrossCursor)
            return

        # build a tiny triangle pixmap for the cursor
        size = 20
        pm = QtGui.QPixmap(size, size)
        pm.fill(QtCore.Qt.transparent)
        g = QtGui.QPainter(pm)
        g.setRenderHint(QtGui.QPainter.Antialiasing)
        g.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 2))
        g.setBrush(QtGui.QBrush(QtGui.QColor(200, 200, 200, 60)))
        poly = QtGui.QPolygon([QtCore.QPoint(size//2, 0),
                            QtCore.QPoint(size//4, size),
                            QtCore.QPoint(size*3//4, size)])
        g.drawPolygon(poly)
        g.end()
        # hot spot at the tip
        self.editor.setCursor(QtGui.QCursor(pm, size//2, 0))


# ------------ main ------------

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    w = Main()
    w.resize(1200, 650)
    w.show()
    app.exec()
