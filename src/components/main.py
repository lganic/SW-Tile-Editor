from .model import MeshModel
from .grid_background import GridBackground
from .preview_overlay import PreviewOverlay
from .editor_view import EditorView
from .preview_widget import PreviewWidget
from .items import VertexItem
from .items import TriangleItem

from PySide6 import QtCore, QtGui, QtWidgets, Shiboken

from sw_ducky import MapGeometry

class Main(QtWidgets.QWidget):
    COLORS = [
        QtGui.QColor('#327986'), QtGui.QColor('#3D8E9F'), QtGui.QColor('#48A3B8'),
        QtGui.QColor('#53B9D1'), QtGui.QColor('#D0D0C6'), QtGui.QColor('#A4B875'),
        QtGui.QColor('#E3D08D'), QtGui.QColor('#53B9D1'), QtGui.QColor('#FFFFFF'),
        QtGui.QColor('#8B6E5C'), QtGui.QColor('#583E2D'),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SW Mesh Editor (WIP)")

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
        self.editor.setSceneRect(-1000, -1000, 2000, 2000)

        self.editor.sceneMouseMoved.connect(self._on_scene_mouse_moved)
        self.editor.sceneLeftClicked.connect(self._on_scene_left_clicked)

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

    def _make_toolbar(self):
        bar = QtWidgets.QToolBar()

        # Create, and attach mesh drop down selector. 
        self.mesh_combo = QtWidgets.QComboBox()
        for i in range(11):
            self.mesh_combo.addItem(['Sea-0', 'Sea-1', 'Sea-2','Sea-3', 'Land', 'Grass', 'Sand', 'Shallows', 'Snow', 'Gravel', 'Rock'][i])
        
        self.mesh_combo.currentIndexChanged.connect(self._on_mesh_changed)
        bar.addWidget(QtWidgets.QLabel(" Active: "))
        bar.addWidget(self.mesh_combo)
        bar.addSeparator()

        # Add buttons for all available tools
        add_vert = QtGui.QAction(bar)
        add_vert.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
        add_vert.setCheckable(True)
        add_vert.setToolTip("Add Vertex")

        make_tri = QtGui.QAction(bar)
        make_tri.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarShadeButton))
        make_tri.setCheckable(True)
        make_tri.setToolTip("Make Triangle")

        del_last_tri = QtGui.QAction(bar)
        del_last_tri.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_TrashIcon))
        del_last_tri.setToolTip("Delete Last Triangle")

        reset_view = QtGui.QAction(bar)
        reset_view.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        reset_view.setToolTip("Reset View")
        
        def on_add_vertex_toggled(checked):
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
            self._update_triangle_cursor(checked)
            self.overlay.update()

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

        add_vert.toggled.connect(on_add_vertex_toggled)
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
                ensure(verts_to_remove, it.model)
                verts_to_remove[it.model].add(it.index)

            elif isinstance(it, TriangleItem):
                ensure(tris_to_remove, it.model)
                tris_to_remove[it.model].add(it.tri_index)
                # disconnect triangle hooks before nuking
                try:
                    it.model.changed.disconnect(it.rebuild_path)
                except (TypeError, RuntimeError):
                    pass

        # also remove any triangles referencing removed vertices
        for m in self.models:
            if m not in verts_to_remove: continue # there are no vertices to remove, continue
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

        overlay = None
        if getattr(self, "overlay", None) and Shiboken.isValid(self.overlay):
            if self.overlay.scene() is self.scene:
                self.scene.removeItem(self.overlay)
            overlay = self.overlay

        ghost = None
        if getattr(self, "ghost_item", None) and Shiboken.isValid(self.ghost_item):
            if self.ghost_item.scene() is self.scene:
                self.scene.removeItem(self.ghost_item)
            ghost = self.ghost_item

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

        if ghost and Shiboken.isValid(ghost):
            self.scene.addItem(ghost)
            self.ghost_item = ghost
        else:
            self.ghost_item = QtWidgets.QGraphicsEllipseItem()
            self.scene.addItem(self.ghost_item)

        if overlay and Shiboken.isValid(overlay):
            self.scene.addItem(overlay)
            self.overlay = overlay
        else:
            self.overlay = PreviewOverlay()
            self.scene.addItem(self.overlay)

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