from PySide6 import QtCore

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
    
    def clear(self):
        self._pts.clear()
        self._tris.clear()
