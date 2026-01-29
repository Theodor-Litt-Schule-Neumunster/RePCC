from pydantic import BaseModel
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QColor, QGuiApplication, QPaintEvent, QRadialGradient
from PyQt5.QtCore import Qt
import sys
import time
import threading
import win32gui
import win32con

# this is so cool

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

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool) # type: ignore[attr-defined]
        self.setAttribute(Qt.WA_TranslucentBackground) # type: ignore[attr-defined]

        # fullscreen over primary screen
        screen = QGuiApplication.primaryScreen().geometry() # type: ignore[attr-defined] 
        self.setGeometry(screen)

        self.dot_x = screen.width() // 2
        self.dot_y = screen.height() // 2

        # makes the cursor be able to click through the widget
        self.make_click_through()
        self.show()

    def make_click_through(self) -> None:
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
    
    def paintEvent(self, a0:QPaintEvent) -> None: # type: ignore[attr-defined]
        """
        Draws the red dot.
        
        :param self:
        :param a0: 
        :type a0: QPaintEvent
        """

        glowradius = 30
        coreradius = 8

        print("Paintevent triggered.")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(Qt.NoPen) # type: ignore[attr-defined]

        gradient = QRadialGradient(self.dot_x, self.dot_y, glowradius)
        gradient.setColorAt(0, QColor(255, 0, 0, 180))
        gradient.setColorAt(.3, QColor(255, 50, 0, 120))
        gradient.setColorAt(.6, QColor(255, 100, 0, 60))
        gradient.setColorAt(1, QColor(255, 0, 0, 0))

        painter.setBrush(gradient)
        painter.drawEllipse(self.dot_x - glowradius, self.dot_y - glowradius,
            glowradius * 2, glowradius * 2)

        coregradient = QRadialGradient(self.dot_x, self.dot_y, coreradius)
        coregradient.setColorAt(0, QColor(255, 255, 255, 255))
        coregradient.setColorAt(0.5, QColor(255, 100, 100, 240))
        coregradient.setColorAt(1, QColor(255, 0, 0, 200))

        painter.setBrush(coregradient)
        painter.drawEllipse(self.dot_x - coreradius, self.dot_y - coreradius,
            coreradius * 2, coreradius * 2)


    def updatePos(self, norm_x:float, norm_y:float) -> None:
        """
        Updates the laserpointer pos and re-draws the overlay.
        
        :param self:
        :param norm_x: A number between 0 - 1 describing how far right the dot is on the screen.
        :type norm_x: float
        :param norm_y: A number between 0 - 1 describing how far down the dot is on the screen.
        :type norm_y: float
        """
        print("recieved pos update with data ", norm_x, norm_y)
        screen = QGuiApplication.primaryScreen().geometry() # type: ignore[attr-defined]

        self.dot_x = int(norm_x * screen.width())
        self.dot_y = int(norm_y * screen.height())

        self.repaint() # New draw on screen.

def _qt_loop():
    print("QT loop running.")
    global App

    App = QApplication(sys.argv)
    sys.exit(App.exec_())
    print("Sys exit.")

async def StartLaserpointer() -> tuple[bool, str]:
    """
    Starts a fullscreen transparent overlay where a laserpointer will be displayed.
    
    :return: bool shows if execution was a success. str is appended message, e.g error.
    :rtype: tuple[bool, str]
    """
    global overlay

    print("Starting laserpointer...")

    try:
        if overlay is None:
            print("Overlay none")
            threading.Thread(target=_qt_loop, daemon=True).start()

            import time
            time.sleep(1)
            print("Praying to god it starts...")
            overlay = LaserOverlay()
            print("IT STARTED!")
        
        else:
            print("Laser is already running. Clear it before starting another.")

        return (True, "Great success!")
    except Exception as e:
        print(e)
        return (False, str(e))
    
async def UpdateLaserpointer(pos: LaserPos) -> tuple[bool, str]:
    """
    Updates the position of the Laserpointer.
    
    :param pos: Position of the laserpointer dot
    :type pos: LaserPos
    :return: shows if execution was a success. str is appended message, e.g error.
    :rtype: tuple[bool, str]
    """
    global overlay

    print("updating overlay")

    try:
        if overlay is None:
            print("not ready")
            return (False, "Overlay is not ready.")
        
        overlay.updatePos(pos.x, pos.y)
        return (True, "Position updates successfully.")
    except Exception as e:
        print(e)
        return (False, str(e))
    
async def ClearLaserpointer() -> tuple[bool, str]:
    """
    Clears the laserpointer.
    
    :return: shows if execution was a success. str is appended message, e.g error.
    :rtype: tuple[bool, str]
    """
    global overlay

    try:
        if overlay is not None:
            overlay.close()
            overlay = None

        return (True, "Overlay cleared.")
    except Exception as e:
        print(e)
        return (False, str(e))