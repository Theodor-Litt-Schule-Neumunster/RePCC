from fastapi import FastAPI
from pydantic import BaseModel
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QColor, QGuiApplication
from PyQt5.QtCore import Qt
import sys
import threading
import win32gui
import win32con

# globals
overlay = None
App = None # App basis: QT

class LaserPos(BaseModel):
    """
    LaserPos Class.
    
    Simple class to represent the current position of the Laserpointer on screen.

    :param pydantic BaseModel:
    """
    x: float
    y: float

class LaserOverlay(QWidget):
    def __init__(self):
        super().__init__()

        # Frameless screen that always stays on top w. transparent bg
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # fullscreen over primary screen
        screen = QGuiApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        self.dot_x = screen.width() // 2
        self.dot_y = screen.height() // 2

        # makes the cursor be able to click through the widget
        self.make_click_through()
        self.show()

    def make_click_through(self):
        """
        make_click_through makes a fullscreen invisible window, where the clicks pass through, 
        so the mouse is not disturbed.
        """
        hwnd = int(self.winId())
        try:
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

            print("Clickthrough OK")
        except Exception as e:
            print("Error at make_click_through, ", e)
    
    def paintEvent():
        ...

    def updatePos():
        ...