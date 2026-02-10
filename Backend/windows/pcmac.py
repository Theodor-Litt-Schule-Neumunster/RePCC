#filever : 0.2 indev

#pyinstaller cmdlet: pyinstaller --onefile --add-data "assets;assets" --collect-all pyfiglet --icon="./assets/repccBin.ico" pcmac.py
# py -3 -m PyInstaller --onefile --add-data "assets;assets" --collect-all pyfiglet --icon="./assets/repccBin.ico" pcmac.py

import os
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
from args import LOGGER_CONF, customerror, forceLogFolder, assetsPath, sendNotification

try:
    logging.config.dictConfig(LOGGER_CONF)
    logger = logging.getLogger("RePCC")
except:
    logger = forceLogFolder()

APPDATA = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore[attr-defined]
HEADER = ".RePCC"
MACDATA = APPDATA + "\\" + HEADER

FILEVER = "0.19"
SPECIAL_KEY_MAP = {
    'ctrl': Key.ctrl,
    'shift': Key.shift,
    'alt': Key.alt,
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
    'cmd_l': Key.cmd_l,
    'cmd_r': Key.cmd_r,
    'ctrl_l': Key.ctrl_l,
    'ctrl_r': Key.ctrl_r,
    'shift_l': Key.shift_l,
    'shift_r': Key.shift_r,
    'alt_l': Key.alt_l,
    'alt_r': Key.alt_r,
    'menu': Key.menu,
    'backspace_l': Key.backspace,
}

class macro():
    def __init__(self) -> None:
        pass

        self.kill = False
        self.pressedkeys = set()
        self.presscombo = {"Key.esc", "'x'"}

        self.listener = None

    def wait(self, time_ms:int|float):
        
        for _ in range(int(time_ms)):
            if self.kill:
                break

            time.sleep(1/1000)

    def _keybindListener(self):

        sendNotification("Macro help", "Press CONTROL and K at the same time to stop the macro.")

        def press(key):

            print(str(key))
            self.pressedkeys.add(str(key))
            print(self.pressedkeys)
            print(self.presscombo)
            print()

            if str(key) == "'\\x0b'": # CTRL + K  
                print("Combo")
                logger.info("Keycombo pressed, killing macro.")
                self.kill = True

        self.listener = Listener(on_press=press)
        with self.listener:
            self.listener.join()

    def startKeyListener(self):
        self.listenerThread = threading.Thread(target=self._keybindListener, daemon=True)
        self.listenerThread.start()

    def verifyStructure(self, jsonFilePath:str, v:bool=False) -> bool:
        """
        Verifies the structure for a macro.\n
        Essential to check if it will cause issues when running.
        
        :param jsonFilePath: the filepath to the JSON file.
        :type jsonFilePath: str
        :param v: makes the function verbose if set to True. Default is False
        :type v: bool
        :return: Returns True if the stucture is valid for macros, false if not.
        :rtype: bool
        """

        # refer to ./bases/structure.json to see macro structure.

        data = None

        try:
            logger.info("pcmac | Atempting to open file to verify the structure...")
            with open(jsonFilePath, "r") as f:

                data = json.load(f)
                f.close()

            logger.info("pcmac | Opened file successfully.")

        except Exception as e:
            logger.error(f"pcmac | File open failed. {e}")

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

            logger.info(f"pcmac | CHECK_keys called for key {key}")
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
                logger.error(customerror("pcmac", e))
                if e.__class__ == KeyError:
                    logger.error("pcmac | -> File does not contain essential keys. Might not be macro format.")
                    return False
                if e.__class__ == IndexError:
                    logger.error("pcmac | -> List index out of range. This could indicate a corrupt file.")
                    return False

                return False

        return False

    def runMacro(self, MacroName:str):
        """
        Runs a macro saved in roaming with its name.\n
        
        :param MacroName: Name of macro. Include .pcmac in the end.
        :type MacroName: str
        :param v: Verbose
        :type v: bool
        """

        print("run mac")

        param_isLoop = None # default if no isloop param is missing
        param_amtLoops = None

        kill = False

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

        def handler_mousemove(x_then:float, y_then:float, transitionTimeMS:float, transition:str):
            logger.info("pcmac | Macro: Moving mouse.")
            
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
            print(steps)

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
                    print("commiting suicide... (MOUSE MOVE)")
                    break

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

            else:
                print("I'm KILLING myself im KILLLLIIINNNNGG myself (click)")
                return
            
        def handler_keyboard(actiontype:str, keys:list, presssleep:int):
            keyboard = Controller()

            logger.info(f"pcmac | Macro: Using keyboard. Type: {actiontype}")
            logger.info(f"pcmac | Macro: Press ladength: " + str(presssleep) + " seconds.")
            logger.info(f"pcmac | Macro: Appended data: {keys}")

            if actiontype == "singlekey":

                for key in keys:
                
                    actual_key = SPECIAL_KEY_MAP.get(key, key)

                    if not key == actual_key:
                        if key == key.upper():

                            key = key.caps_lock

                    if not self.kill:

                        keyboard.press(actual_key) # type: ignore[attr-defined]
                        self.wait(presssleep+0.002)
                        keyboard.release(actual_key) # type: ignore[attr-defined]
                    
                    else:
                        print("man im dead")
                        break
                
            if actiontype == "multikey":

                actual_keys = []

                if not self.kill:
                    for key in keys:
                        key_lower = key.lower()
                        actual_key = SPECIAL_KEY_MAP.get(key_lower, key_lower)
                        actual_keys.append(actual_key)

                        keyboard.press(actual_key) # type: ignore[attr-defined]

                    self.wait(presssleep+0.002)

                    for key in reversed(actual_keys):
                        keyboard.release(key)

        try:
            macropath = MACDATA + "\\macros\\" + MacroName
            if not os.path.exists(macropath):
                raise ValueError("Macro does not exsist in saved.")
            
            data = None
            with open(macropath, "r") as f:
                data = json.load(f)
                f.close()
                print(data)

            def run():

                for step in data:
                    if step == "$data":
                        logger.info("pcmac | Macro: Setp is data. Skipping.")
                        continue

                    actiondata = data[step]["actiondata"]
                    
                    logger.info("pcmac | Macro: Waiting before executing next step...")
                    logger.info("pcmac | Macro: " + str(data[step]["sleep"]/1000) + " seconds.")
                    self.wait(data[step]["sleep"]+0.001)

                    if self.kill: break
                    
                    if data[step]["type"] == "mouse" and data[step]["actiontype"] == "move":
                        handler_mousemove(actiondata[0], actiondata[1], data[step]["transitiontime"], data[step]["transition"])
                        continue

                    if data[step]["type"] == "mouse" and data[step]["actiontype"] == "click":
                        handler_mouseclick(actiondata[0], data[step]["presssleep"])
                        continue
                    
                    if data[step]["type"] == "keyboard":
                        handler_keyboard(data[step]["actiontype"], actiondata, data[step]["presssleep"])
                        continue

                if self.kill:
                    sendNotification("Macro status", "Forced macro to shut down with keycombo")
                    return

            if "$data" in data:
                logger.info("main | macro: Macro has included data, extracting...")
                handler_data(data["$data"])
                logger.info(f"main | macro: extracted data: { data['$data'] }")

            failsafe = 0

            try:

                if param_isLoop == True:
                    self.startKeyListener()
                    while True:

                        if self.kill or failsafe == 10: 
                            if self.listener:
                                self.listener.stop()
                            if self.listenerThread:
                                self.listenerThread.join()

                            print("kill inf")
                            break

                        print("call")
                        run()

                elif param_amtLoops > 1 and not param_amtLoops == None: # type: ignore[attr-defined]
                    self.startKeyListener()
                    for i in range(int(param_amtLoops)): # type: ignore[attr-defined]

                        if self.kill: 
                            if self.listener:
                                self.listener.stop()
                            if self.listenerThread:
                                self.listenerThread.join()

                            print("kill amnt")
                            break

                        print("amt call")
                        print(i+1)
                        run()
                        return
            except Exception:
                print("Fail inside")

                if not Exception.__class__ == KeyboardInterrupt:

                    self.startKeyListener()
                    print("singleloop")
                    run()

            if self.kill: self.kill = False
            return

        except Exception as e:
            logger.error(customerror("pcmac", e))


def initializePCMAC(v:bool=False):

    filestructure = {
        ".RePCC": [
            "macros",
            "settings",
            "assets",
            "logs"
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
        logger.info(f"pcmac | regedit: Attempting.")
        def restartExplorer():
            try:
                logger.info(f"pcmac | regedit: Restarting explorer.exe...")
                subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])
                subprocess.run(["explorer.exe"])
                logger.info(f"pcmac | regedit: Successfully restarted explorer.")
            except Exception as e:
                logger.error(customerror("pcmac", e))
        if ctypes.windll.shell32.IsUserAnAdmin():
            logger.info(f"pcmac | regedit: Is running with administrative privileges.")
            def keySearch():
                try:
                    key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".pcmac")
                    winreg.CloseKey(key)
                    return True
                except FileNotFoundError:
                    logger.info(f"pcmac | regedit: Key does not exsist.")
                    return False
        
            if not keySearch():
                ext_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, ".pcmac")
                winreg.SetValueEx(ext_key, None, 0, winreg.REG_SZ, "RePCC_File")
                winreg.CloseKey(ext_key)
                progid_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "RePCC_File")
                winreg.SetValueEx(progid_key, None, 0, winreg.REG_SZ, "RePCC File")
                icon_key = winreg.CreateKey(progid_key, "DefaultIcon")
                winreg.SetValueEx(icon_key, None, 0, winreg.REG_SZ, MACDATA+"\\assets\\script.ico") # Takes ico from roaming repcc
                winreg.CloseKey(icon_key)
                winreg.CloseKey(progid_key)

                logger.info(f"pcmac | regedit: Successfully created all keys.")
                restartExplorer()
            else:
                logger.info(f"pcmac | regedit: Key exsits.")
        else:
            logger.error(customerror("pcmac", "Script is not running as administrator. Can not complete registry verification."))

        logger.info(f"pcmac | regedit: Done.")
    
    logger.info("pcmac | Running verification...")
    logger.info(f"pcmac | Current filestructure version: {str(FILEVER)}")

    versionVerification()
    regVerification()

if __name__ == "__main__":
    #initializePCMAC()
    mac=macro()

    #mac.verifyStructure("./base/structure.json")
    mac.runMacro("testMouseMove.pcmac")