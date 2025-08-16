from PySide6 import QtCore, QtGui, QtWidgets
from typing import Any

def darklight_switch(lightmode_object: Any, darkmode_object: Any):
    '''
    Switch objects based on current styling mode. 
    '''

    # Load color scheme
    hints = QtGui.QGuiApplication.styleHints()
    scheme = hints.colorScheme()

    is_dark = (scheme == QtCore.Qt.ColorScheme.Dark)

    if is_dark:
        return darkmode_object
    
    return lightmode_object

def darklight_from_lightcolor(r, g, b, a = 255):

    light_color = QtGui.QColor(r, g, b, a)
    dark_color = QtGui.QColor(255 - r, 255 - g, 255 - b, a)

    return darklight_switch(light_color, dark_color)