import math
from PySide6 import QtCore

def snap_axis(value: float, size: float) -> float:

    '''
    Snap a coordinate, to a certain rounding specification. 

    I.e: Snapping the value 15.7 with a bounding size of 5, will give the value of 15, since that is the closest value which satisfies: k*S=v where k is an integer, S is 5, and v is 15.7
    '''

    output = size * math.floor((value + (size / 2)) / size) # might be an easier way to do this, but this is what I've figured out. 

    return max(-500, min(500, output)) # Clamp to tile range. 


def snap_point(point: QtCore.QPointF, size: float) -> QtCore.QPointF:

    x = point.x()
    y = point.y()

    new_x = snap_axis(x, size)
    new_y = snap_axis(y, size)

    return QtCore.QPointF(new_x, new_y)


if __name__ == '__main__':

    print(snap_axis(-15.6, 5))