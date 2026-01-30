import os
import sys
import yaml
import logging
import threading
import win32gui
import win32con
import logging.config

from pydantic import BaseModel
from collections import deque
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QColor, QGuiApplication, QPaintEvent, QRadialGradient
from PyQt5.QtCore import Qt, QTimer, QMetaObject, Q_ARG, pyqtSlot, pyqtSignal

from args import LOGGER_CONF, customerror

# this is so cool

# globals
logging.config.dictConfig(LOGGER_CONF)
logger = logging.getLogger("RePCC")

overlay = None
App = None # App basis: QT
overlay_ready = threading.Event()

APPDATA = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming\\.RePCC" # type: ignore[attr-defined]
SETTINGS = APPDATA+"\\settings\\"

class LaserPos(BaseModel):
    """
    LaserPos Class.
    
    Simple class to represent the current position of the Laserpointer on screen.

    :param pydantic BaseModel:
    """
    x: float
    y: float

class LaserOverlay(QWidget):
    # Signal to update position from any thread
    positionUpdate = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()

        # Frameless screen that always stays on top w. transparent bg

        loaded_settings = yaml.safe_load(open(SETTINGS+"presentationTools.yaml"))
        self.loaded_settings = loaded_settings

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool) # type: ignore[attr-defined]
        self.setAttribute(Qt.WA_TranslucentBackground) # type: ignore[attr-defined]

        # fullscreen over primary screen
        screen = QGuiApplication.primaryScreen().geometry() # type: ignore[attr-defined] 
        self.setGeometry(screen)

        self.opacity = 0

        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.timeout.connect(self.fadeout_start)

        self.fadetimer = QTimer(self)
        self.fadetimer.timeout.connect(self.fadeout_step)

        self.dot_x = screen.width() // 2
        self.dot_y = screen.height() // 2

        self.trail = deque(maxlen=20)

        self.positionUpdate.connect(self._updatePosInternal)

        # makes the cursor be able to click through the widget
        self.make_click_through()
        self.show()

    
    def fadeout_reset(self):

        time = self.loaded_settings["laserpointer"].get("fadetime", 1000)

        self.inactivity_timer.stop()
        self.fadetimer.stop()
        self.opacity = 1
        self.inactivity_timer.start(time)
        self.repaint()

    def fadeout_start(self):
        self.fadetimer.start(50)

    def fadeout_step(self):
        self.opacity -= 0.05
        if self.opacity <= 0:
            self.opacity = 0
            self.fadetimer.stop()
        self.repaint()

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

        except Exception as e:
            logger.error("Laser | ERROR @ laser.py/LaserOverlay/make_click_through")
            logger.error(customerror("Laser", e))
    
    def paintEvent(self, a0:QPaintEvent) -> None: # type: ignore[attr-defined]
        """
        Draws the red dot.
        
        :param self:
        :param a0: 
        :type a0: QPaintEvent
        """

        if self.opacity <= 0:
            return

        glowradius = 30
        coreradius = 8

        style = self.loaded_settings["laserpointer"].get("style", "default")

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(Qt.NoPen) # type: ignore[attr-defined]

        if style == "default":

            gradient = QRadialGradient(self.dot_x, self.dot_y, glowradius)
            gradient.setColorAt(0, QColor(255, 0, 0, int(180* self.opacity)))
            gradient.setColorAt(.3, QColor(255, 50, 0, int(120* self.opacity)))
            gradient.setColorAt(.6, QColor(255, 100, 0, int(60* self.opacity)))
            gradient.setColorAt(1, QColor(255, 0, 0, 0))

            painter.setBrush(gradient)
            painter.drawEllipse(self.dot_x - glowradius, self.dot_y - glowradius,
                glowradius * 2, glowradius * 2)

            coregradient = QRadialGradient(self.dot_x, self.dot_y, coreradius)
            coregradient.setColorAt(0, QColor(255, 255, 255, int(225* self.opacity)))
            coregradient.setColorAt(0.5, QColor(255, 100, 100, int(240* self.opacity)))
            coregradient.setColorAt(1, QColor(255, 0, 0, int(200* self.opacity)))

            painter.setBrush(coregradient)
            painter.drawEllipse(self.dot_x - coreradius, self.dot_y - coreradius,
                coreradius * 2, coreradius * 2)
        
        elif style == "trail":
            for i, (tx, ty) in enumerate(reversed(list(self.trail))):
                if i == 0:
                    continue

                trail_opacity = max(0, self.opacity * (1 - i / len(self.trail)))
                trail_glowradius = max(0, glowradius * (1 - i / len(self.trail)) * 0.5)
                
                if trail_opacity <= 0 or trail_glowradius <= 0:
                    continue

                gradient = QRadialGradient(tx, ty, trail_glowradius)
                gradient.setColorAt(0, QColor(255, 0, 0, int(180 * trail_opacity)))
                gradient.setColorAt(.3, QColor(255, 50, 0, int(120 * trail_opacity)))
                gradient.setColorAt(.6, QColor(255, 100, 0, int(60 * trail_opacity)))
                gradient.setColorAt(1, QColor(255, 0, 0, 0))
                painter.setBrush(gradient)
                painter.drawEllipse(int(tx - trail_glowradius), int(ty - trail_glowradius),
                    int(trail_glowradius * 2), int(trail_glowradius * 2)) 

            gradient = QRadialGradient(self.dot_x, self.dot_y, glowradius)
            gradient.setColorAt(0, QColor(255, 0, 0, int(180* self.opacity)))
            gradient.setColorAt(.3, QColor(255, 50, 0, int(120* self.opacity)))
            gradient.setColorAt(.6, QColor(255, 100, 0, int(60* self.opacity)))
            gradient.setColorAt(1, QColor(255, 0, 0, 0))

            painter.setBrush(gradient)
            painter.drawEllipse(self.dot_x - glowradius, self.dot_y - glowradius,
                glowradius * 2, glowradius * 2)

            coregradient = QRadialGradient(self.dot_x, self.dot_y, coreradius)
            coregradient.setColorAt(0, QColor(255, 255, 255, int(225* self.opacity)))
            coregradient.setColorAt(0.5, QColor(255, 100, 100, int(240* self.opacity)))
            coregradient.setColorAt(1, QColor(255, 0, 0, int(200* self.opacity)))
            
            painter.setBrush(coregradient)
            painter.drawEllipse(self.dot_x - coreradius, self.dot_y - coreradius,
                coreradius * 2, coreradius * 2)

        elif style == "simple":
            painter.setBrush(QColor(255, 0, 0, 255))
            painter.drawEllipse(self.dot_x - coreradius, self.dot_y - coreradius,
                coreradius * 2, coreradius * 2)

    @pyqtSlot(float, float)
    def _updatePosInternal(self, norm_x: float, norm_y: float) -> None:
        """Internal slot that runs on the Qt thread."""
        screen = QGuiApplication.primaryScreen().geometry() # type: ignore[attr-defined]

        self.dot_x = int(norm_x * screen.width())
        self.dot_y = int(norm_y * screen.height())

        self.trail.append((self.dot_x, self.dot_y))

        self.fadeout_reset()
        self.repaint()

    def updatePos(self, norm_x:float, norm_y:float) -> None:
        """
        Updates the laserpointer pos and re-draws the overlay.
        Thread-safe: can be called from any thread.
        """
        # Emit signal to ensure update happens on Qt thread
        self.positionUpdate.emit(norm_x, norm_y)

def _qt_loop():
    print("QT loop running.")
    global App, overlay

    App = QApplication(sys.argv)
    
    # Create overlay in the Qt thread
    overlay = LaserOverlay()
    logger.debug("Laser | Overlay started successfully.")
    overlay_ready.set()  # Signal that overlay is ready
    
    sys.exit(App.exec_())

async def StartLaserpointer() -> tuple[bool, str]:
    """
    Starts a fullscreen transparent overlay where a laserpointer will be displayed.
    
    :return: bool shows if execution was a success. str is appended message, e.g error.
    :rtype: tuple[bool, str]
    """
    global overlay, overlay_ready

    logger.debug("Laser | Starting overlay...")

    try:
        if overlay is None:
            print("Overlay none")
            overlay_ready.clear()
            threading.Thread(target=_qt_loop, daemon=True).start()

            # Wait for overlay to be created (with timeout)
            if not overlay_ready.wait(timeout=5):
                return (False, "Timeout waiting for overlay to start")
        
        else:
            logger.debug("Laser | Can only run one overlay at a time.")

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

    try:
        if overlay is None:
            print("not ready")
            return (False, "Overlay is not ready.")
        
        overlay.updatePos(pos.x, pos.y)
        return (True, "Position updates successfully.")
    except Exception as e:
        logger.error("Laser | ERROR @ laser.py/UpdateLaserpointer")
        logger.error(customerror("Laser", e))
        return (False, str(e))
    
async def ClearLaserpointer() -> tuple[bool, str]:
    """
    Clears the laserpointer.
    
    :return: shows if execution was a success. str is appended message, e.g error.
    :rtype: tuple[bool, str]
    """
    global overlay

    logger.debug("Laser | Killed overlay.")

    try:
        if overlay is not None:
            overlay.close()
            overlay = None

        return (True, "Overlay cleared.")
    except Exception as e:
        logger.error("Laser | ERROR @ laser.py/ClearLaserpointer")
        logger.error(customerror("Laser", e))
        return (False, str(e))