#filever : 0.2 indev

# pyinstaller cmdlet: pyinstaller --onefile --add-data "assets;assets" --icon="./assets/repccBin.ico" pcmac.py
# py -3 -m PyInstaller --onefile --add-data "assets;assets" --icon="./assets/repccBin.ico" pcmac.py

import os
import sys
import json
import time
import shutil
import ctypes
import winreg
import logging
import win32api
import win32con
import threading
import subprocess
import logging.config

from pynput.keyboard import Controller, Key, Listener, KeyCode
from args import LOGGER_CONF, customerror, forceLogFolder, assetsPath, sendNotification, log_exception, log_state, safe_log_value

# Windows process creation flag to hide console windows
CREATE_NO_WINDOW = 0x08000000

try:
    logging.config.dictConfig(LOGGER_CONF)
    logger = logging.getLogger("RePCC")
except:
    logger = forceLogFolder()

APPDATA = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming"
HEADER = ".RePCC"
MACDATA = APPDATA + "\\" + HEADER
ROAMING = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming"

ERROR_LOG_PATH = ROAMING + "\\.RePCC\\logs\\errors.txt"
try:
    os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)
    sys.stderr = open(ERROR_LOG_PATH, "a", buffering=1)
except Exception:
    pass

FILEVER = "0.195"
SPECIAL_KEY_MAP = {
    'ctrl': Key.ctrl,
    'control': Key.ctrl,
    'ctl': Key.ctrl,
    'shift': Key.shift,
    'shiftkey': Key.shift,
    'alt': Key.alt,
    'option': Key.alt,
    'alt_gr': Key.alt_gr,
    'altgr': Key.alt_gr,
    'enter': Key.enter,
    'return': Key.enter,  # Alias
    'tab': Key.tab,
    'esc': Key.esc,
    'escape': Key.esc,  # Alias
    'backspace': Key.backspace,
    'delete': Key.delete,
    'home': Key.home,
    'end': Key.end,
    'page_up': Key.page_up,
    'page_down': Key.page_down,
    'up': Key.up,
    'down': Key.down,
    'left': Key.left,
    'right': Key.right,
    'space': Key.space,
    'caps_lock': Key.caps_lock,
    'num_lock': Key.num_lock,
    'scroll_lock': Key.scroll_lock,
    'print_screen': Key.print_screen,
    'pause': Key.pause,
    'insert': Key.insert,
    'f1': Key.f1,
    'f2': Key.f2,
    'f3': Key.f3,
    'f4': Key.f4,
    'f5': Key.f5,
    'f6': Key.f6,
    'f7': Key.f7,
    'f8': Key.f8,
    'f9': Key.f9,
    'f10': Key.f10,
    'f11': Key.f11,
    'f12': Key.f12,
    'f13': Key.f13,
    'f14': Key.f14,
    'f15': Key.f15,
    'f16': Key.f16,
    'f17': Key.f17,
    'f18': Key.f18,
    'f19': Key.f19,
    'f20': Key.f20,
    'cmd': Key.cmd,
    'win': Key.cmd,
    'windows': Key.cmd,
    'super': Key.cmd,
    'cmd_l': Key.cmd_l,
    'cmd_r': Key.cmd_r,
    'left_win': Key.cmd_l,
    'right_win': Key.cmd_r,
    'ctrl_l': Key.ctrl_l,
    'ctrl_r': Key.ctrl_r,
    'left_ctrl': Key.ctrl_l,
    'right_ctrl': Key.ctrl_r,
    'lctrl': Key.ctrl_l,
    'rctrl': Key.ctrl_r,
    'shift_l': Key.shift_l,
    'shift_r': Key.shift_r,
    'left_shift': Key.shift_l,
    'right_shift': Key.shift_r,
    'lshift': Key.shift_l,
    'rshift': Key.shift_r,
    'alt_l': Key.alt_l,
    'alt_r': Key.alt_r,
    'left_alt': Key.alt_l,
    'right_alt': Key.alt_r,
    'lalt': Key.alt_l,
    'ralt': Key.alt_r,
    'menu': Key.menu,
    'backspace_l': Key.backspace,
    'pgup': Key.page_up,
    'pgdn': Key.page_down,
    'del': Key.delete,
    'ins': Key.insert,
    'spacebar': Key.space,
}


def normalize_macro_key_token(raw_key: str) -> str:
    key = str(raw_key).strip().lower().replace("-", "_").replace(" ", "_")

    alias_map = {
        "control": "ctrl",
        "ctl": "ctrl",
        "leftcontrol": "left_ctrl",
        "rightcontrol": "right_ctrl",
        "leftalt": "left_alt",
        "rightalt": "right_alt",
        "leftshift": "left_shift",
        "rightshift": "right_shift",
        "pageup": "page_up",
        "pagedown": "page_down",
        "return": "enter",
        "escape": "esc",
    }

    return alias_map.get(key, key)

class macro():
    def __init__(self) -> None:
        self.kill = False
        self.listener = None
        self.listenerThread = None
        self.listener_active = False
        logger.debug("pcmac | macro instance created")

    def wait(self, time_ms:int|float):
        total_ms = max(int(time_ms), 0)
        if total_ms >= 100:
            logger.debug(f"pcmac | wait start | duration_ms={total_ms} | kill={self.kill}")
        
        for _ in range(total_ms):
            if self.kill:
                logger.info(f"pcmac | wait interrupted | duration_ms={total_ms}")
                break

            time.sleep(1/1000)

        if total_ms >= 100:
            logger.debug(f"pcmac | wait end | duration_ms={total_ms} | kill={self.kill}")

    def _keybindListener(self):
        logger.info("pcmac | key listener starting")
        self.listener_active = True
        logger.info("pcmac | key listener armed for CTRL+K")

        def press(key):
            if not self.listener_active:
                logger.debug("pcmac | key listener ignoring key because listener is inactive")
                return False

            logger.debug(f"pcmac | key listener received key={safe_log_value(key)}")
            if str(key) == "'\\x0b'": # CTRL + K  
                print("Combo")
                logger.info("Keycombo pressed, killing macro.")
                self.kill = True
                return False

        self.listener = Listener(on_press=press)
        try:
            with self.listener:
                self.listener.join()
        finally:
            self.listener_active = False
            self.listener = None
            logger.info("pcmac | key listener stopped")

    def startKeyListener(self):
        logger.debug("pcmac | startKeyListener invoked")
        self.stopKeyListener()

        try:
            sendNotification("Macro help", "Press CONTROL and K at the same time to stop the macro.")
            logger.info("pcmac | key listener help notification sent")
        except Exception as e:
            log_exception(logger, "pcmac", "macro/startKeyListener/notification", e)

        self.listenerThread = threading.Thread(target=self._keybindListener, daemon=True)
        self.listenerThread.name = f"macro-key-listener-{id(self)}"
        self.listenerThread.start()
        logger.info(f"pcmac | key listener thread started | name={self.listenerThread.name}")

    def stopKeyListener(self):
        logger.debug("pcmac | stopKeyListener invoked")
        self.listener_active = False

        if self.listener:
            try:
                self.listener.stop()
                logger.info("pcmac | key listener stop requested")
            except Exception as e:
                log_exception(logger, "pcmac", "macro/stopKeyListener/stop", e)

        current_thread = threading.current_thread()
        if self.listenerThread and self.listenerThread.is_alive() and self.listenerThread is not current_thread:
            self.listenerThread.join(timeout=1.5)
            logger.info(
                f"pcmac | key listener thread join attempted | name={self.listenerThread.name} | alive={self.listenerThread.is_alive()}"
            )

        self.listenerThread = None

    def verifyStructure(self, jsonFilePathOrJSONdata:str|dict) -> bool:
        """
        Verifies the structure for a macro.\n
        Essential to check if it will cause issues when running.
        
        :param jsonFilePathOrJSONdata: the filepath to the JSON file or JSON data.
        :type jsonFilePathOrJSONdata: str | dict
        :param v: makes the function verbose if set to True. Default is False
        :type v: bool
        :return: Returns True if the stucture is valid for macros, false if not.
        :rtype: bool
        """

        # refer to ./bases/structure.json to see macro structure.

        data = None
        datatype = "PATH"

        if not os.path.exists(str(jsonFilePathOrJSONdata)): # type: ignore
            datatype = "JSON"

        log_state(logger, "pcmac.verifyStructure.input", datatype=datatype, source=jsonFilePathOrJSONdata)

        try:
            if datatype == "PATH":
                logger.info("pcmac | Atempting to open file to verify the structure...")
                with open(jsonFilePathOrJSONdata, "r") as f: # type: ignore

                    data = json.load(f)
                    f.close()

                logger.info("pcmac | Opened file successfully.")
            
            if datatype == "JSON":
                data = jsonFilePathOrJSONdata # type: ignore
                logger.info("pcmac | Recieved JSON to check")

        except Exception as e:
            logger.error("pcmac | ERROR @ pcmac.py/macro/verifyStructure")
            log_exception(logger, "pcmac", "macro/verifyStructure/open", e, source=jsonFilePathOrJSONdata, datatype=datatype)

            return False
        
        def CHECK_layout(req:list, data:dict) -> bool:
            logger.info(f"pcmac | CHECK_layout called")

            con = [key for key in req if key in data]

            if con == req:
                logger.info(f"pcmac | CHECK_layout returned OK")
                return True
            
            return False

        def CHECK_keys(req:list, keytype:str, data:dict, i:int):

            allowedTransitions = ["linear", "quadratic"]

            logger.info(f"pcmac | CHECK_keys called for key {i}")
            logger.info(f"        Appended data:")
            logger.info(f"        {req}")
            logger.info(f"        {data}")
            logger.info(f"        {i}")

            print(data)
            
            if not CHECK_layout(req, data):
                raise ValueError(f"""
Keys don't match up to requirements.
   Should be: {req}
   Is:        {[key for key in data]}""")

            if not type(data["actiondata"]) == list:
                raise ValueError(f"""
Type for ActionData is incorrect.
   Should be: list
   Is:        {type(data["actiondata"]).__name__}""")

            if keytype == "keyboard" and data["actiontype"] == "singlekey":

                if not len(data["actiondata"]) >= 1:
                    raise ValueError(f"""
ActionData length for singlekey keyboard is not correct.
   Should be: x>=1
   Is:        {len(data["actiondata"])}""")

            if keytype == "keyboard" and data["actiontype"] == "multikey":

                if not len(data["actiondata"]) > 1:
                    raise ValueError(f"""
ActionData length for multikey keyboard is not correct.
   Should be: x > 1
   Is:        {len(data["actiondata"])}""")

            if keytype == "mouse" and data["actiontype"] == "click":

                if not data["actiondata"] == [0] and not data["actiondata"] == [1]:
                    raise ValueError(f"""
ActionData value for click mouse is not correct.
   Should be: 0 || 1
   Is:        {data["actiondata"][0]}""")

            if keytype == "mouse" and data["actiontype"] == "move":

                if not [type(val).__name__ for val in data["actiondata"]] == ["float", "float"]:
                    raise ValueError(f"""
ActionData for move mouse is the wrong format.
   Should be: ['float', 'float']
   Is         {[type(val).__name__ for val in data["actiondata"]]}""")
            
            if "presssleep" in req:
                if not data["presssleep"] >= 0:
                    raise ValueError(f"""
PressSleep value is outside of range.
   Should be: x >= 0
   Is:        {data["presssleep"]}""")

            if "transition" and "transitiontime" in req:

                if not data["transition"] in allowedTransitions:
                    raise ValueError(f"""
Transition is not allowed.
   Should be: {allowedTransitions}
   Is:        {data["transition"]}""")

                if not data["transitiontime"] >= 0:
                    raise ValueError(f"""
TransitionTime is outside of range.
   Should be: x >= 0
   Is:        {data["transitiontime"]}""")

            if not data["sleep"] >= 0:
                raise ValueError(f"""
Sleep is outside of range.
   Should be: x >= 0
   Is:        {data["sleep"]}""")
            
            logger.info(f"pcmac | CHECK_key returned OK.")
        
        if type(data) == dict:

            reqApplication = ["type", "actiontype", "actiondata", "sleep"]
            reqKeyboardAndStaticMouse = ["type", "actiontype", "actiondata", "sleep", "presssleep"]
            reqMovingMouse = ["type", "actiontype", "actiondata", "sleep", "transition", "transitiontime"]

            try:
                for key in data:
                    logger.debug(f"pcmac | verifyStructure inspecting key={key} value={safe_log_value(data[key])}")
                    if key == "$data":
                        logger.info("pcmac | Key is $data, skipping.")
                        continue
                    if data[key]["type"] == "keyboard" or (data[key]["type"] == "mouse" and data[key]["actiontype"] == "click"):
                        CHECK_keys(reqKeyboardAndStaticMouse, data[key]["type"], data[key], int(key))
                        continue
                    
                    if data[key]["type"] == "mouse" and data[key]["actiontype"] == "move":
                        CHECK_keys(reqMovingMouse, data[key]["type"], data[key], int(key))
                        continue

                    if data[key]["type"] == "application":
                        CHECK_keys(reqApplication, data[key]["type"], data[key], int(key))
                        continue

                    raise ValueError("Parsed type does not exsist in current macro format.")
                
                return True
                    
            except Exception as e:
                logger.error("pcmac | ERROR @ pcmac.py/macro/verifyStructure")
                log_exception(logger, "pcmac", "macro/verifyStructure/validate", e, parsed_keys=list(data.keys()))
                if e.__class__ == KeyError:
                    logger.error("pcmac | -> File does not contain essential keys. Might not be macro format.")
                    return False
                if e.__class__ == IndexError:
                    logger.error("pcmac | -> List index out of range. This could indicate a corrupt file.")
                    return False

                return False

        return False

    def presenter(self, presenterKey:str):
        logger.info(f"pcmac | presenter invoked | presenterKey={presenterKey}")

        def press(key):
            logger.debug(f"pcmac | presenter pressing key={safe_log_value(key)}")

            keyboard = Controller()
            keyboard.press(key)
            time.sleep(.05)
            keyboard.release(key)

        key = SPECIAL_KEY_MAP.get(presenterKey, None)
        logger.debug(f"pcmac | presenter resolved key={safe_log_value(key)}")

        if not key == None:
            press(key)
        else:
            logger.warning(f"pcmac | presenter key not found | presenterKey={presenterKey}")

    def runMacro(self, MacroName:str):
        """
        Runs a macro saved in roaming with its name.\n
        
        :param MacroName: Name of macro. Include .pcmac in the end.
        :type MacroName: str
        :param v: Verbose
        :type v: bool
        """

        param_isLoop = None # default if no isloop param is missing
        param_amtLoops = None
        active_step = None
        self.kill = False
        logger.info(f"pcmac | runMacro invoked | macro={MacroName} | thread={threading.current_thread().name}")

        def handler_data(data:dict):

            nonlocal param_isLoop
            nonlocal param_amtLoops
            
            if "isLoop" in data:
                param_isLoop = data["isLoop"]
                logger.info(f"pcmac | macro: set loop to { param_isLoop }")
                print(f"updated: {param_isLoop}")
            
            if "amtLoops" in data:
                param_amtLoops = data["amtLoops"]
                logger.info(f"pcmac | macro: set amount of loops to {param_amtLoops}")

            log_state(logger, "pcmac.runMacro.data", param_isLoop=param_isLoop, param_amtLoops=param_amtLoops)

        def handler_mousemove(x_then:float, y_then:float, transitionTimeMS:float, transition:str):
            logger.info("pcmac | Macro: Moving mouse.")
            log_state(logger, "pcmac.runMacro.mousemove.start", x_then=x_then, y_then=y_then, transitionTimeMS=transitionTimeMS, transition=transition)
            
            def easing(x:float) -> float:

                    if x <= 0:
                        return 0.0
                    if x >= 1:
                        return 1.0

                    return 2*x**2 - x**4
            
            screen_width = win32api.GetSystemMetrics(0) # width in PX
            screen_height = win32api.GetSystemMetrics(1) # height in PX

            # Convert normalized to absolute
            x_abs_then = int(x_then * screen_width)
            y_abs_then = int(y_then * screen_height)
            x_now, y_now = win32api.GetCursorPos()

            x_delta = x_abs_then - x_now
            y_delta = y_abs_then - y_now

            steps = max(int(transitionTimeMS*60), 1)
            sleep_time = transitionTimeMS / steps
            log_state(logger, "pcmac.runMacro.mousemove.calculated", screen_width=screen_width, screen_height=screen_height, x_abs_then=x_abs_then, y_abs_then=y_abs_then, x_now=x_now, y_now=y_now, x_delta=x_delta, y_delta=y_delta, steps=steps, sleep_time=sleep_time)

            for i in range(steps + 1):

                transitionProgress = i / steps

                smoothProgress = easing(transitionProgress)
                x_new, y_new = (None, None)

                if transition == "quadratic":
                    x_new = int(x_now + x_delta * smoothProgress)
                    y_new = int(y_now + y_delta * smoothProgress)

                if transition == "linear":
                    x_new = int(x_now + x_delta * transitionProgress)
                    y_new = int(y_now + y_delta * transitionProgress)

                if not self.kill:

                    win32api.SetCursorPos((x_new, y_new))
                    if i < steps:
                        self.wait(sleep_time+0.005)
                
                else: 
                    logger.info(f"pcmac | Macro: Mouse move interrupted at step {i}/{steps}")
                    break

            logger.debug("pcmac | Macro: Mouse move complete")

        def handler_mouseclick(button:int, pressSleep:int):

            logger.info(f"pcmac | Macro: Clicking mouse. Button: {button}")
            logger.info(f"pcmac | Macro: Press length: " + str(pressSleep/1000) + " seconds.")

            if not self.kill:
            
                if button == 0:
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0,0)
                    self.wait(pressSleep+0.001)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0,0)

                if button == 1:
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0,0)
                    self.wait(pressSleep+0.001)
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0,0)
                logger.debug(f"pcmac | Macro: Mouse click complete | button={button}")

            else:
                logger.info("pcmac | Macro: Mouse click skipped because kill flag is set")
                return
            
        def handler_keyboard(actiontype:str, keys:list, presssleep:int):
            keyboard = Controller()

            logger.info(f"pcmac | Macro: Using keyboard. Type: {actiontype}")
            logger.info(f"pcmac | Macro: Press ladength: " + str(presssleep) + " seconds.")
            logger.info(f"pcmac | Macro: Appended data: {keys}")

            if actiontype == "singlekey":

                for key in keys:
                    normalized = normalize_macro_key_token(key)
                    actual_key = SPECIAL_KEY_MAP.get(normalized, key)
                    logger.debug(f"pcmac | Macro: singlekey resolved | raw={safe_log_value(key)} | normalized={normalized} | actual={safe_log_value(actual_key)}")

                    if not self.kill:

                        keyboard.press(actual_key) # type: ignore[attr-defined]
                        self.wait(presssleep+0.002)
                        keyboard.release(actual_key) # type: ignore[attr-defined]
                    
                    else:
                        break
                
            if actiontype == "multikey":

                actual_keys = []

                if not self.kill:
                    for key in keys:
                        normalized = normalize_macro_key_token(key)
                        actual_key = SPECIAL_KEY_MAP.get(normalized, key)
                        actual_keys.append(actual_key)
                        logger.debug(f"pcmac | Macro: multikey resolved | raw={safe_log_value(key)} | normalized={normalized} | actual={safe_log_value(actual_key)}")

                        keyboard.press(actual_key) # type: ignore[attr-defined]

                    self.wait(presssleep+0.002)

                    for key in reversed(actual_keys):
                        keyboard.release(key)

        try:
            macropath = MACDATA + "\\macros\\" + MacroName
            log_state(logger, "pcmac.runMacro.paths", macropath=macropath, macdata=MACDATA)
            if not os.path.exists(macropath):
                raise ValueError("Macro does not exsist in saved.")
            
            data = None
            with open(macropath, "r") as f:
                data = json.load(f)
                f.close()
                print(data)
            log_state(logger, "pcmac.runMacro.loaded", keys=list(data.keys()), metadata=data.get("$data") if isinstance(data, dict) else None)

            def run():
                nonlocal active_step
                logger.info(f"pcmac | Macro: run loop starting | total_steps={len(data)}")

                for step in data:
                    active_step = step
                    if step == "$data":
                        logger.info("pcmac | Macro: Setp is data. Skipping.")
                        continue

                    actiondata = data[step]["actiondata"]
                    log_state(logger, "pcmac.runMacro.step", step=step, step_data=data[step])
                    
                    logger.info("pcmac | Macro: Waiting before executing next step...")
                    logger.info("pcmac | Macro: " + str(data[step]["sleep"]/1000) + " seconds.")
                    self.wait(data[step]["sleep"]+0.001)

                    if self.kill:
                        logger.info(f"pcmac | Macro: breaking before step execution because kill was set | step={step}")
                        break
                    
                    try:
                        if data[step]["type"] == "mouse" and data[step]["actiontype"] == "move":
                            handler_mousemove(actiondata[0], actiondata[1], data[step]["transitiontime"], data[step]["transition"])
                            continue

                        if data[step]["type"] == "mouse" and data[step]["actiontype"] == "click":
                            handler_mouseclick(actiondata[0], data[step]["presssleep"])
                            continue
                        
                        if data[step]["type"] == "keyboard":
                            handler_keyboard(data[step]["actiontype"], actiondata, data[step]["presssleep"])
                            continue

                        logger.warning(f"pcmac | Macro: Unhandled step type encountered | step={step} | type={data[step].get('type')} | actiontype={data[step].get('actiontype')}")
                    except Exception as e:
                        log_exception(logger, "pcmac", "macro/runMacro/step", e, macro=MacroName, step=step, step_data=data[step])
                        raise

                if self.kill:
                    logger.info(f"pcmac | Macro: run loop exiting due to kill flag | macro={MacroName}")
                    return

                logger.info(f"pcmac | Macro: run loop completed | macro={MacroName}")

            if "$data" in data:
                logger.info("main | macro: Macro has included data, extracting...")
                handler_data(data["$data"])
                logger.info(f"main | macro: extracted data: { data['$data'] }")

            try:
                log_state(logger, "pcmac.runMacro.mode", param_isLoop=param_isLoop, param_amtLoops=param_amtLoops)

                if param_isLoop == True:
                    self.startKeyListener()
                    logger.info(f"pcmac | Macro: entering infinite loop mode | macro={MacroName}")
                    while True:

                        if self.kill: 
                            self.stopKeyListener()
                            logger.info(f"pcmac | Macro: loop mode stopped by kill flag | macro={MacroName}")
                            break

                        run()

                        if self.kill:
                            self.stopKeyListener()
                            logger.info(f"pcmac | Macro: infinite loop exiting after killed iteration | macro={MacroName}")
                            break

                elif param_amtLoops > 1 and not param_amtLoops == None: # type: ignore[attr-defined]
                    self.startKeyListener()
                    logger.info(f"pcmac | Macro: entering fixed loop mode | macro={MacroName} | loops={param_amtLoops}")
                    for loop_index in range(int(param_amtLoops)): # type: ignore[attr-defined]
                        logger.info(f"pcmac | Macro: fixed loop iteration starting | macro={MacroName} | iteration={loop_index + 1}/{int(param_amtLoops)}")
                        
                        if self.kill: 
                            self.stopKeyListener()
                            logger.info(f"pcmac | Macro: fixed loop stopped by kill flag | macro={MacroName}")
                            break

                        logger.debug(f"pcmac | Macro: invoking run() for fixed loop iteration {loop_index + 1}")
                        run()

                        if self.kill:
                            self.stopKeyListener()
                            logger.info(f"pcmac | Macro: fixed loop exiting after killed iteration | macro={MacroName} | iteration={loop_index + 1}")
                            break

                else:
                    self.startKeyListener()
                    logger.info(f"pcmac | Macro: entering single-run mode | macro={MacroName}")
                    logger.debug("pcmac | Macro: invoking run() for single-run mode")
                    run()

                    if self.kill:
                        logger.info(f"pcmac | Macro: single-run exited after kill flag | macro={MacroName}")
            except Exception as e:
                log_exception(logger, "pcmac", "macro/runMacro/loop-wrapper", e, macro=MacroName, active_step=active_step, param_isLoop=param_isLoop, param_amtLoops=param_amtLoops)
                if e.__class__ != KeyboardInterrupt:

                    print("error, so single")
                    logger.warning(f"pcmac | Macro: loop wrapper failed, retrying single run | macro={MacroName}")

                    self.startKeyListener()
                    run()

            finally:
                self.stopKeyListener()

            if self.kill:
                logger.info(f"pcmac | Macro: resetting kill flag after run | macro={MacroName}")
                self.kill = False
            logger.info(f"pcmac | runMacro finished | macro={MacroName}")
            return

        except Exception as e:
            logger.error("pcmac | ERROR @ pcmac.py/macro/runMacro")
            log_exception(logger, "pcmac", "macro/runMacro", e, macro=MacroName, active_step=active_step, listener_started=self.listenerThread is not None)

def initializePCMAC():

    filestructure = {
        ".RePCC": [
            "macros",
            "settings",
            "assets",
            "logs",
            "data"
        ],
    }
    def fileVerification():
        
        for key in filestructure:
            if not os.path.exists(APPDATA+"\\"+key):
                os.mkdir(APPDATA+"\\"+key)
                logger.info(f"pcmac | verif: Created folder {key}")
            if (type(filestructure[key]) == dict or type(filestructure[key]) == list) and len(filestructure[key]) > 0:
                for subkey in filestructure[key]:
                    dir = APPDATA+"\\"+key+"\\"+subkey
                    
                    if not os.path.exists(dir):
                        os.mkdir(dir)
                        logger.info(f"pcmac | verif: Created subfolder {subkey} for {key}")
                        if subkey == "assets":
                            shutil.copyfile(assetsPath("assets/repcclogo.ico"), MACDATA+"\\assets\\repcc.ico")
                            shutil.copyfile(assetsPath("assets/scriptlogo.ico"), MACDATA+"\\assets\\script.ico")
                            logger.info(f"pcmac | verif: Assets cloned into assets")
                        if subkey == "data": 
                            filedir = assetsPath("assets/_data/register.yaml")
                            shutil.copyfile(filedir, MACDATA+"\\data\\register.yaml")

                    if os.path.exists(MACDATA+"\\settings\\"):
                        defaultsettingdir = assetsPath("assets/_settings/")
                        usersettigdir = MACDATA+"\\settings\\"

                        if not len(os.listdir(defaultsettingdir)) == len(os.listdir(usersettigdir)):
                            logger.info(f"pcmac | verif: Settings length missmatch")

                            for file in os.listdir(defaultsettingdir):
                                filedir = assetsPath("assets/_settings/"+file)

                                if not file in os.listdir(usersettigdir):
                                    shutil.copyfile(filedir, MACDATA+"\\settings\\"+file)

                            logger.info(f"pcmac | verif: Settings OK")

        with open(MACDATA+"\\version", "w") as f:
            f.write(FILEVER)
            f.close()
        logger.info(f"pcmac | verif: Done.")
        
    def versionVerification():
        
        if os.path.exists(MACDATA+"\\version"):
            version = 0
            with open(MACDATA+"\\version", "r+") as f:
                
                version = f.read()
                f.close()
            if str(version) == FILEVER:
                logger.info("pcmac | Fileversion matches.")
            else:
                logger.info("pcmac | Fileversion does not match. Forcing file verification...")
                fileVerification()
        else:
            logger.info("pcmac | Fileversion noes not exsist. Forcing file verification...")
            fileVerification()
    
    def regVerification():

        # NOTE: Change in the future to check every key
        # NOTE: Primary application will be in APPDATA/Roaming/.RePCC/Application

        logger.info(f"pcmac | regedit: Attempting.")
        registryChanged = False

        def restartExplorer():
            try:
                logger.info(f"pcmac | regedit: Restarting explorer.exe...")
                subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], creationflags=CREATE_NO_WINDOW)
                subprocess.run(["explorer.exe"], creationflags=CREATE_NO_WINDOW)
                logger.info(f"pcmac | regedit: Successfully restarted explorer.")
            except Exception as e:
                logger.error(customerror("pcmac", e))

        def ensure_registry_value(root, key_path:str, value_name:str|None, expected_value:str):
            nonlocal registryChanged

            key = winreg.CreateKey(root, key_path)
            current_value = None

            try:
                current_value, _ = winreg.QueryValueEx(key, value_name)
            except FileNotFoundError:
                current_value = None

            if current_value != expected_value:
                winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, expected_value)
                registryChanged = True
                logger.info(f"pcmac | regedit: Set value for HKCR\\{key_path} ({'(Default)' if value_name is None else value_name}).")

            winreg.CloseKey(key)

        if ctypes.windll.shell32.IsUserAnAdmin():
            logger.info(f"pcmac | regedit: Is running with administrative privileges.")
            try:
                if getattr(sys, "frozen", False):
                    openfileExe = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "openfile.exe")
                else:
                    openfileExe = os.path.join(os.environ.get("ProgramW6432", os.environ.get("ProgramFiles", "C:\\Program Files")), "RePCC", "openfile.exe")
                openCommand = f'"{openfileExe}" "%1"'

                ensure_registry_value(winreg.HKEY_CLASSES_ROOT, ".pcmac", None, "RePCC_File")
                ensure_registry_value(winreg.HKEY_CLASSES_ROOT, "RePCC_File", None, "RePCC File")
                ensure_registry_value(winreg.HKEY_CLASSES_ROOT, "RePCC_File\\DefaultIcon", None, MACDATA+"\\assets\\script.ico")
                ensure_registry_value(winreg.HKEY_CLASSES_ROOT, "RePCC_File\\shell", None, "open")
                ensure_registry_value(winreg.HKEY_CLASSES_ROOT, "RePCC_File\\shell\\open", None, "Open with RePCC")
                ensure_registry_value(winreg.HKEY_CLASSES_ROOT, "RePCC_File\\shell\\open\\command", None, openCommand)

                if registryChanged:
                    logger.info(f"pcmac | regedit: Registry keys verified and updated.")
                    restartExplorer()
                else:
                    logger.info(f"pcmac | regedit: All required keys already exist and are correct.")

            except Exception as e:
                logger.error("pcmac | ERROR @ pcmac.py/initializePCMAC/regVerification")
                logger.error(customerror("pcmac", e))
        else:
            logger.error(customerror("pcmac", "Script is not running as administrator. Can not complete registry verification."))

        logger.info(f"pcmac | regedit: Done.")
    
    logger.info("pcmac | Running verification...")
    logger.info(f"pcmac | Current filestructure version: {str(FILEVER)}")

    versionVerification()
    regVerification()

if __name__ == "__main__":
    initializePCMAC()

logger.warning("pcmac | HIT FILE END.")