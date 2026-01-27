#filever : 0.2 indev

#pyinstaller cmdlet: pyinstaller --onefile --add-data "assets;assets" --collect-all pyfiglet --icon="./assets/repcclogo.ico" pcmac.py

import os
import sys
import json
import time
import shutil
import ctypes
import winreg
import argparse
import pyfiglet
import win32api
import win32con
import subprocess

from pynput.keyboard import Controller, Key

os.system("cls")

APPDATA = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore[attr-defined]
HEADER = ".RePCC"
MACDATA = APPDATA + "\\" + HEADER

FILEVER = "0.15"
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

SILLY = True

def assetsPath(relativepath:str):
    """
    For easy file access in py script or binary
    
    :param relativepath: Relative filepath for asset. e. g. /assets/repcclogo.ico
    """
    basepath = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(basepath, relativepath)

class macro():
    def __init__(self) -> None:
        pass

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
            if v: print("Attempting to open file")
            with open(jsonFilePath, "r") as f:

                data = json.load(f)
                f.close()

            if v: print("File opened and loaded successfully.")

        except Exception as e:
            if v: print("Error occured trying to open file: " + str(e))
            return False
        
        def CHECK_layout(req:list, data:dict) -> bool:
            # 67
            if v: print("   $ Checking if layout inside is correct...")

            con = [key for key in req if key in data]

            if con == req:
                if v: print("   > Keys are OK.")
                return True
            
            return False

        def CHECK_keys(req:list, keytype:str, data:dict, i:int):
            
            # for the love of christ, please dont judge me. i tried my best :(

            allowedTransitions = ["linear", "quadratic"]

            if v: print(" ! Check called for: " + keytype)
            
            if not CHECK_layout(req, data):
                raise ValueError(f"""
Keys don't match up to requirements.
   Should be: {req}
   Is:        {[key for key in data]}""")

            if v: print("   $ Checking ActionData...")

            if not type(data["actiondata"]) == list:
                raise ValueError(f"""
Type for ActionData is incorrect.
   Should be: list
   Is:        {type(data["actiondata"]).__name__}""")

            if keytype == "keyboard" and data["actiontype"] == "singlekey":
                if v: print("   * is single key")

                if not len(data["actiondata"]) >= 1:
                    raise ValueError(f"""
ActionData length for singlekey keyboard is not correct.
   Should be: x>=1
   Is:        {len(data["actiondata"])}""")

            if keytype == "keyboard" and data["actiontype"] == "multikey":
                if v: print("   * is multi key")

                if not len(data["actiondata"]) > 1:
                    raise ValueError(f"""
ActionData length for multikey keyboard is not correct.
   Should be: x > 1
   Is:        {len(data["actiondata"])}""")

            if keytype == "mouse" and data["actiontype"] == "click":
                if v: print("   * is click")

                if not data["actiondata"] == [0] and not data["actiondata"] == [1]:
                    raise ValueError(f"""
ActionData value for click mouse is not correct.
   Should be: 0 || 1
   Is:        {data["actiondata"][0]}""")

            if keytype == "mouse" and data["actiontype"] == "move":
                if v: print("   * is move")

                if not [type(val).__name__ for val in data["actiondata"]] == ["float", "float"]:
                    raise ValueError(f"""
ActionData for move mouse is the wrong format.
   Should be: ['float', 'float']
   Is         {[type(val).__name__ for val in data["actiondata"]]}""")
            
            if v: print("   > ActionData is OK.")

            if "presssleep" in req:
                if v: print("   $ Checking PressSleep time...")
                if not data["presssleep"] > 0:
                    raise ValueError(f"""
PressSleep value is outside of range.
   Should be: x > 0
   Is:        {data["presssleep"]}""")

                if v: print("   > PressSleep is OK.")

            if "transition" and "transitiontime" in req:
                if v: print("   $ Checking transition values...")

                if not data["transition"] in allowedTransitions:
                    raise ValueError(f"""
Transition is not allowed.
   Should be: {allowedTransitions}
   Is:        {data["transition"]}""")

                if not data["transitiontime"] > 0:
                    raise ValueError(f"""
TransitionTime is outside of range.
   Should be: x > 0
   Is:        {data["transitiontime"]}""")
                
                if v: print("   > Transition values are OK.")

            if v: print("   $ Checking Sleep time...")

            if not data["sleep"] > 0:
                raise ValueError(f"""
Sleep is outside of range.
   Should be: x > 0
   Is:        {data["sleep"]}""")

            if v: print("   > Sleep is OK.")

            if v: print(" ! Values are OK.")
        
        if type(data) == dict:
            if v: print("------------------------------------")
            if v: print("Data is correct type")

            reqApplication = ["type", "actiontype", "actiondata", "sleep"]
            reqKeyboardAndStaticMouse = ["type", "actiontype", "actiondata", "sleep", "presssleep"]
            reqMovingMouse = ["type", "actiontype", "actiondata", "sleep", "transition", "transitiontime"]

            try:
                for key in data:
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
                print("Something went wrong when attempting to verify file integrity:")
                if e.__class__ == KeyError:
                    print("File does not contain essential keys. Might not be macro format.")
                    return False
                if e.__class__ == IndexError:
                    print("List index out of range. This could indicate a corrupt file.")
                    return False
                
                print(e)
                return False

        return False

    def runMacro(self, MacroName:str, v:bool=True):
        """
        Runs a macro saved in roaming with its name.\n
        
        :param MacroName: Name of macro. Include .pcmac in the end.
        :type MacroName: str
        :param v: Verbose
        :type v: bool
        """

        def handler_mousemove(x_then:float, y_then:float, transitionTimeMS:float, transition:str):
            if v: print("\n  Is mouse move.")
            
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

            transitionTimeSEC = transitionTimeMS / 1000
            steps = max(int(transitionTimeSEC*60), 1)
            sleep_time = transitionTimeSEC / steps

            for i in range(steps + 1):

                transitionProgress = i / steps

                smoothProgress = easing(transitionProgress)
                x_new, y_new = (None, None)

                if transition == "quadratic":
                    if v: print("  Mouse is moving with style. " + str(smoothProgress))
                    x_new = int(x_now + x_delta * smoothProgress)
                    y_new = int(y_now + y_delta * smoothProgress)

                if transition == "linear":
                    if v: print("  Mouse is moving linear. " + str(transitionProgress))
                    x_new = int(x_now + x_delta * transitionProgress)
                    y_new = int(y_now + y_delta * transitionProgress)

                win32api.SetCursorPos((x_new, y_new))
                if i < steps:
                    time.sleep(sleep_time+0.001)

        def handler_mouseclick(button:int, pressSleep:int):

            if v: print("  Mouse click")
            if v: print("  Press length: " + str(pressSleep/1000) + " seconds.")
            
            if button == 0:
                if v: print("  Click is left mouse button")
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0,0)
                time.sleep(pressSleep/1000+0.001)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0,0)

            if button == 1:
                if v: print("  Click is right mouse button")
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0,0)
                time.sleep(pressSleep/1000+0.001)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0,0)

            if v: print("  Mouse click finished.")
            
        def handler_keyboard(actiontype:str, keys:list, presssleep:int):
            keyboard = Controller()

            if v: print("  Keyboard")
            if v: print("  Press for " + str(presssleep/1000) + " seconds.")

            if actiontype == "singlekey":

                if v: print("  Single key presses")

                for key in keys:
                
                    lowkey = key.lower() # haha
                    actual_key = SPECIAL_KEY_MAP.get(key, key)

                    if not key == actual_key:
                        if key == key.upper():

                            key = key.caps_lock

                    if v: print("    " + str(actual_key))

                    keyboard.press(actual_key) # type: ignore[attr-defined]
                    time.sleep(presssleep/1000+0.001)
                    keyboard.release(actual_key) # type: ignore[attr-defined]
            
            if actiontype == "multikey":
                if v: print("  Multi key press")

                actual_keys = []

                for key in keys:
                    key_lower = key.lower()
                    actual_key = SPECIAL_KEY_MAP.get(key_lower, key_lower)
                    actual_keys.append(actual_key)

                    if v: print("    " + str(actual_key))

                    keyboard.press(actual_key) # type: ignore[attr-defined]

                time.sleep(presssleep/1000+0.001)

                if v: print("  Releasing all keys...")

                for key in reversed(actual_keys):
                    keyboard.release(key)
                
            print("   Keyboard press done.")

        try:
            macropath = MACDATA + "\\macros\\" + MacroName
            if not os.path.exists(macropath):
                raise ValueError("Macro does not exsist in saved.")
            
            data = None
            with open(macropath, "r") as f:
                data = json.load(f)
                f.close()

            for step in data:

                actiondata = data[step]["actiondata"]
                
                if v: print("\nWaiting before executing next step...")
                if v: print(str(data[step]["sleep"]/1000) + " seconds.")
                time.sleep(data[step]["sleep"]/1000+0.001)
                
                if data[step]["type"] == "mouse" and data[step]["actiontype"] == "move":
                    handler_mousemove(actiondata[0], actiondata[1], data[step]["transitiontime"], data[step]["transition"])
                    continue

                if data[step]["type"] == "mouse" and data[step]["actiontype"] == "click":
                    handler_mouseclick(actiondata[0], data[step]["presssleep"])
                    continue
                
                if data[step]["type"] == "keyboard":
                    handler_keyboard(data[step]["actiontype"], actiondata, data[step]["presssleep"])
                    continue

        except Exception as e:
            print("Failed to execute macro.")
            print(e)

macroHandler = macro()
#macroHandler.verifyStructure("./base/structure.json", True)
#macroHandler.runMacro("mouseTest.pcmac", True)

if __name__ == "__main__":

    def init(v:bool=False):
        os.system("cls")

        if v: print("\n")
        if v: print(pyfiglet.figlet_format("RePCC", font="slant"))
        if v: print("\ninit says \"Hello World!\"")

        # Reference to how the folders are build, ver 0.15
        filestructure = {
            ".RePCC": [
                "macros",
                "settings",
                "assets"
            ],
        }

        def fileVerification():
            if v: print("\nInit forced a structure verification")
            for key in filestructure:

                if not os.path.exists(APPDATA+"\\"+key):
                    os.mkdir(APPDATA+"\\"+key)
                    if v: print("> ROAMING\\" + key + " has been created.")
                else:
                    if v: print("> ROAMING\\" + key + " already exists.")

                if (type(filestructure[key]) == dict or type(filestructure[key]) == list) and len(filestructure[key]) > 0:
                    if v: print("  " + key + " has subfolders.")
                    for subkey in filestructure[key]:
                        dir = APPDATA+"\\"+key+"\\"+subkey
                        if not os.path.exists(dir):
                            os.mkdir(dir)
                            if v: print("    > *\\"+subkey+" has been created.")

                            if subkey == "assets":
                                shutil.copyfile(assetsPath("assets/repcclogo.ico"), MACDATA+"\\assets\\repcc.ico")
                                if v: print("        > copied RePCC icon asset folder")
                                shutil.copyfile(assetsPath("assets/scriptlogo.ico"), MACDATA+"\\assets\\script.ico")
                                if v: print("        > copied script icon into asset folder")
                        
                        else:
                            if v: print("    > *\\"+subkey+" already exists.")

            with open(MACDATA+"\\version", "w") as f:
                f.write(FILEVER)
                f.close()

            if v: print("Verification done. Updated version to: " + FILEVER)
            
        def versionVerification():

            if os.path.exists(MACDATA+"\\version"):

                if v: print("Version file exsists, checking version.")

                version = 0
                with open(MACDATA+"\\version", "r+") as f:
                    
                    version = f.read()
                    f.close()

                if v: print("Version is: ", version)

                if str(version) == FILEVER:
                    if v: print("Version matches, skipping file verification.")
                else:
                    if v: print("Version not matching, verifying structure...")
                    fileVerification()
            else:
                if v: print("Version file does not exsist. Verifying structure...")
                fileVerification()

        def regVerification():
            if v: print("\nRegistry verification.")

            def restartExplorer():
                try:

                    if v: print("\nRestarting \"explorer.exe\"")

                    subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])
                    subprocess.run(["explorer.exe"])

                    if v: print("Explorer started successfully.")

                except Exception as e:
                    if v: print("restartExplorer failed! Whoops!\nError: ", str(e))

            if ctypes.windll.shell32.IsUserAnAdmin():
                if v: print("Script is running as administrator.")

                def keySearch():
                    try:
                        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".pcmac")
                        winreg.CloseKey(key)

                        return True
                    except FileNotFoundError:
                        if v: print("Key does not exsist.")
                        return False
            
                if not keySearch():

                    if v: print("\nCreating keys")

                    ext_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, ".pcmac")
                    winreg.SetValueEx(ext_key, None, 0, winreg.REG_SZ, "RePCC_File")
                    winreg.CloseKey(ext_key)

                    if v: print("    > Created extension key \".pcmac\" and closed key")

                    progid_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "RePCC_File")
                    winreg.SetValueEx(progid_key, None, 0, winreg.REG_SZ, "RePCC File")

                    if v: print("    > Created program id key \"RePCC_File\"")

                    icon_key = winreg.CreateKey(progid_key, "DefaultIcon")
                    winreg.SetValueEx(icon_key, None, 0, winreg.REG_SZ, MACDATA+"\\assets\\script.ico") # Takes ico from roaming repcc

                    if v: print("        > Created subkey \"Default\"")

                    winreg.CloseKey(icon_key)
                    if v: print("* Closed icon key")
                    winreg.CloseKey(progid_key)
                    if v: print("* Closed program id key")

                    restartExplorer()
                else:
                    if v: print("Key \".pcmac\" exsists.")
            else:
                if v: print("Script is not running as administrator. Can not complete registry verification.")

        if v: print("Running verification. Current version: " + str(FILEVER))
        if v: print("------------------------------------")

        versionVerification()
        regVerification()

        if v: print("------------------------------------")
    def main():

        def initParser():

            parser = argparse.ArgumentParser(
                description="Reads or saves a macro",
                epilog="Will not work if no arguments are parsed."
            )

            parser.add_argument(
                "-v", "--verbose",
                action="store_true",
                help="Makes the function EXTRA transparent",
                default="None"
            )

            parser.add_argument(
                "-j", "--json",
                type=str,
                default="None",
                help="JSON format as a string. Macro data in json",
            )

            parser.add_argument(
                "-n", "--name",
                type=str,
                help="If save: saves macro with given name. If read: searches for macro with given name",
                default="none"
            )

            parser.add_argument(
                "-m", "--mode",
                choices=["save", "read"],
                default="none",
            )

            parser.add_argument(
                "-a", "--all",
                action="store_true",
                help="Prints out all the availible data, if accepted. Used in: read -a"
            )

            args = parser.parse_args()
            return args
        
        args = initParser()

        init(args.verbose)

        # may the IFs take over this file.
        # (I apologize in advance.)

        def printAllFiles(listdir):
            for i in range(0, len(listdir)):
                name = listdir[i][:-6]
                print("    " + str(i+1) + ". " + name)
        
        if args.mode == "read": # If we are trying to read a file...

            listdir = os.listdir(MACDATA+"\\macros")

            if len(listdir) == 0: # ... but there are no files availible to read...

                print("No files avalible to read.") # ... then we yell at the user!
                return

            if args.name == "none": # ... but no name was set ...

                if args.all: # ... but the user used "all"

                    print("Here are all availible files:")
                    printAllFiles(listdir) # we give the user all files
                    return

                print("No name given to read. Here are the avalible files:") # ... then we yell at the user ...
                printAllFiles(listdir) # ... and give them all the avalible file names

                return

            if not args.name == "none": # ... and the user gave us a name ...

                name = args.name

                if not name[-6:] == ".pcmac": # ... and the parsed name does not end with ".pcmac" ...

                    name = name + ".pcmac" # ... we add .pcmac to the end of the name ...

                if name in listdir: # ... and the name is inside the macro directory ...

                    data = None

                    with open(MACDATA+"\\macros\\"+name, "r") as f: # ... we open the designated file ...
                        data = f.read()
                        f.close()

                    print(data)
                    return data # ... and return the contents

                if not name in listdir: # ... and the name is not inside the macro directory...

                    print("File does not exsist. Here are all availible files:") # ... we yell at the user ...
                    printAllFiles(listdir) # ... and give them all the avalible file names

        if args.mode == "save": # If the user is trying to save a macro ...

            if args.json == "none": # ... but no JSON data was parsed ...
                print("No JSON string parsed.") # ... we yell at the user.
                return

            if not args.json == "none": 
                ...

                # TODO: Finish intigration of writing new macro
        
        if args.mode == "none":
            print("Must have MODE set.")

    #main()