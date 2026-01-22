
import os
import sys
import json
import shutil
import ctypes
import winreg
import subprocess

from pyfiglet import figlet_format



APPDATA = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore[attr-defined]
HEADER = ".RePCC"
MACDATA = APPDATA + "\\" + HEADER

FILEVER = "0.15"

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