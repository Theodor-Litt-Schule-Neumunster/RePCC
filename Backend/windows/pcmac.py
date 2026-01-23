
import os
import sys
import json
import shutil
import ctypes
import winreg
import argparse
import subprocess

from pyfiglet import figlet_format

APPDATA = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore[attr-defined]
HEADER = ".RePCC"
MACDATA = APPDATA + "\\" + HEADER

FILEVER = "0.15"

class macro():
    def __init__(self) -> None:
        pass

    

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

if __name__ == "__main__":

    def init():
        os.system("cls")

        print("\n")
        print(figlet_format("RePCC", font="slant"))
        print("\ninit says \"Hello World!\"")

        # Reference to how the folders are build, ver 0.15
        filestructure = {
            ".RePCC": [
                "macros",
                "settings",
                "assets"
            ],
        }

        def fileVerification():
            print("\nInit forced a structure verification")
            for key in filestructure:

                if not os.path.exists(APPDATA+"\\"+key):
                    os.mkdir(APPDATA+"\\"+key)
                    print("> ROAMING\\" + key + " has been created.")
                else:
                    print("> ROAMING\\" + key + " already exists.")

                if (type(filestructure[key]) == dict or type(filestructure[key]) == list) and len(filestructure[key]) > 0:
                    print("  " + key + " has subfolders.")
                    for subkey in filestructure[key]:
                        dir = APPDATA+"\\"+key+"\\"+subkey
                        if not os.path.exists(dir):
                            os.mkdir(dir)
                            print("    > *\\"+subkey+" has been created.")

                            if subkey == "assets":
                                dir = os.path.dirname(__file__)
                                shutil.copyfile(dir+"\\assets\\repcclogo.ico", MACDATA+"\\assets\\repcc.ico")
                                print("        > copied RePCC icon asset folder")
                                shutil.copyfile(dir+"\\assets\\scriptlogo.ico", MACDATA+"\\assets\\script.ico")
                                print("        > copied script icon into asset folder")
                        
                        else:
                            print("    > *\\"+subkey+" already exists.")

            with open(MACDATA+"\\version", "w") as f:
                f.write(FILEVER)

            print("Verification done. Updated version to: " + FILEVER)
            
        def versionVerification():

            if os.path.exists(MACDATA+"\\version"):

                print("Version file exsists, checking version.")

                version = 0
                with open(MACDATA+"\\version", "r+") as f:
                    
                    version = f.read()
                    f.close()

                print("Version is: ", version)

                if str(version) == FILEVER:
                    print("Version matches, skipping file verification,")
                else:
                    print("Version not matching, verifying structure...")
                    fileVerification()
            else:
                print("Version file does not exsist. Verifying structure...")
                fileVerification()

        def regVerification():
            print("\nRegistry verification.")

            def restartExplorer():
                try:

                    print("\nRestarting \"explorer.exe\"")

                    subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])
                    subprocess.run(["explorer.exe"])

                    print("Explorer started successfully.")

                except Exception as e:
                    print("restartExplorer failed! Whoops!\nError: ", str(e))

            if ctypes.windll.shell32.IsUserAnAdmin():
                print("Script is running as administrator.")

                def keySearch():
                    try:
                        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".pcmac")
                        winreg.CloseKey(key)

                        return True
                    except FileNotFoundError:
                        print("Key does not exsist.")
                        return False
            
                if not keySearch():

                    print("\nCreating keys")

                    ext_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, ".pcmac")
                    winreg.SetValueEx(ext_key, None, 0, winreg.REG_SZ, "RePCC_File")
                    winreg.CloseKey(ext_key)

                    print("    > Created extension key \".pcmac\" and closed key")

                    progid_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "RePCC_File")
                    winreg.SetValueEx(progid_key, None, 0, winreg.REG_SZ, "RePCC File")

                    print("    > Created program id key \"RePCC_File\"")

                    icon_key = winreg.CreateKey(progid_key, "DefaultIcon")
                    winreg.SetValueEx(icon_key, None, 0, winreg.REG_SZ, MACDATA+"\\assets\\script.ico")

                    print("        > Created subkey \"Default\"")

                    winreg.CloseKey(icon_key)
                    print("* Closed icon key")
                    winreg.CloseKey(progid_key)
                    print("* Closed program id key")

                    restartExplorer()
                else:
                    print("Key \".pcmac\" exsists.")
            else:
                print("Script is not running as administrator. Can not complete registry verification.")

        print("Running verification. Current version: " + str(FILEVER))
        print("------------------------------------")

        versionVerification()
        regVerification()

        print("------------------------------------")

    #init()
    main()