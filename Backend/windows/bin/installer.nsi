!include MUI2.nsh
!include WinVer.nsh

Name "RePCC"
OutFile "RePCC-Setup.exe"
InstallDir "$PROGRAMFILES64\RePCC"
RequestExecutionLevel admin
CRCCheck force
SetCompressor /SOLID lzma
SetOverwrite ifnewer
AllowRootDirInstall false

!define AUTOSTART_TASK_NAME "RePCC Autostart"

!define BANNER_HEADER "${__FILEDIR__}\banner.bmp"
!define BANNER_SIDE "${__FILEDIR__}\banner_welcome.bmp"

!define MUI_ICON "${__FILEDIR__}\installicon.ico"
!define MUI_UNICON "${__FILEDIR__}\uninstall.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "${BANNER_HEADER}"
!define MUI_HEADERIMAGE_UNBITMAP "${BANNER_HEADER}"
!define MUI_WELCOMEFINISHPAGE_BITMAP "${BANNER_SIDE}"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "${BANNER_SIDE}"
!define MUI_BRANDINGTEXT "RePCC Installer"


!define MUI_LICENSEPAGE_TEXT_TOP "Please review the GPL-3.0 license for RePCC."
!define MUI_LICENSEPAGE_TEXT_BOTTOM "A click-through acceptance is not required to receive a copy. Click Continue to proceed."
!define MUI_LICENSEPAGE_BUTTON "Continue"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.rtf"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_RUN "$INSTDIR\main.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch RePCC now"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!define MUI_FINISHPAGE_TITLE "RePCC is ready"
!define MUI_FINISHPAGE_TEXT "Setup has completed successfully. You can launch RePCC now or open the welcome guide."
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\welcome.html"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Open welcome guide"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_COMPONENTS
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "German"

LangString DESC_SEC_MAIN ${LANG_ENGLISH} "Main is the main program of RePCC."
LangString DESC_SEC_MAIN ${LANG_GERMAN} "Main ist das Hauptprogramm von RePCC."
LangString DESC_SEC_OPENFILE ${LANG_ENGLISH} "OpenFile is called when a .pcmac file is opened."
LangString DESC_SEC_OPENFILE ${LANG_GERMAN} "OpenFile wird aufgerufen, wenn eine .pcmac-Datei geöffnet wird."
LangString DESC_SEC_AUTOSTART ${LANG_ENGLISH} "Starts automatically when the user signs in to their account."
LangString DESC_SEC_AUTOSTART ${LANG_GERMAN} "Startet automatisch, wenn sich der Benutzer am Konto anmeldet."
LangString DESC_UNSEC_CLOSE ${LANG_ENGLISH} "Closes running RePCC processes before uninstalling files."
LangString DESC_UNSEC_CLOSE ${LANG_GERMAN} "Schließt laufende RePCC-Prozesse, bevor Dateien deinstalliert werden."
LangString DESC_UNSEC_MAIN ${LANG_ENGLISH} "Removes installed RePCC files, scheduled task, and uninstall registry keys."
LangString DESC_UNSEC_MAIN ${LANG_GERMAN} "Entfernt installierte RePCC-Dateien, den geplanten Task und Deinstallations-Registryeinträge."
LangString DESC_UNSEC_APPDATA ${LANG_ENGLISH} "Optionally removes user data in %APPDATA%\\.RePCC."
LangString DESC_UNSEC_APPDATA ${LANG_GERMAN} "Entfernt optional Benutzerdaten in %APPDATA%\\.RePCC."

Function .onInit
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP|MB_OK "RePCC requires Windows 10 or Windows 11. Setup will now exit."
    Abort
  ${EndIf}

  ReadRegStr $R0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "UninstallString"
  ReadRegStr $R2 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "InstallLocation"

  StrCmp $R0 "" 0 found_old

  ReadRegStr $R0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "UninstallString"
  ReadRegStr $R2 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "InstallLocation"

found_old:
  StrCmp $R0 "" done

  StrCmp $R2 "" +2
  StrCpy $INSTDIR $R2

  MessageBox MB_ICONQUESTION|MB_YESNO "An existing RePCC installation was found.$\r$\n$\r$\nSelect Yes to upgrade in-place (recommended), or No to cancel setup." IDYES do_upgrade
  Abort

do_upgrade:
  ExecWait '$R0 /S' $R1
  IntCmp $R1 0 done
  MessageBox MB_ICONSTOP|MB_OK "Upgrade preparation failed while running the existing uninstaller (exit code: $R1). Setup will now exit."
  Abort

done:
FunctionEnd

Section "Main (required)" SEC_MAIN
  SectionIn RO
  SetOutPath "$INSTDIR"

  ClearErrors
  File "main.exe"
  File "welcome.html"
  IfErrors 0 +2
  Abort "Failed to copy required application files."

  ClearErrors
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  IfErrors 0 +2
  Abort "Failed to create uninstaller."

  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "DisplayName" "RePCC"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "DisplayIcon" "$INSTDIR\main.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "Publisher" "TLS"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "NoRepair" 1

  System::Call 'shell32::SHChangeNotify(i,i,p,p) v (0x08000000,0,0,0)'

SectionEnd

Section "Install openfile integration" SEC_OPENFILE
  SetOutPath "$INSTDIR"

  ClearErrors
  File "openfile.exe"
  IfErrors 0 +2
  Abort "Failed to copy openfile.exe."

  ClearErrors
  WriteRegStr HKCR ".pcmac" "" "RePCC_File"
  WriteRegStr HKCR "RePCC_File" "" "RePCC File"
  WriteRegStr HKCR "RePCC_File\DefaultIcon" "" "$APPDATA\.RePCC\assets\script.ico"
  WriteRegStr HKCR "RePCC_File\shell" "" "open"
  WriteRegStr HKCR "RePCC_File\shell\open" "" "Open with RePCC"
  WriteRegStr HKCR "RePCC_File\shell\open\command" "" '"$INSTDIR\openfile.exe" "%1"'
  IfErrors 0 +2
  Abort "Failed to register .pcmac file association keys."

  System::Call 'shell32::SHChangeNotify(i,i,p,p) v (0x08000000,0,0,0)'
SectionEnd

Section "Enable start with Windows" SEC_AUTOSTART
  IfFileExists "$INSTDIR\main.exe" +3 0
  MessageBox MB_ICONEXCLAMATION|MB_OK "RePCC installed, but autostart could not be configured because main.exe was not found in $INSTDIR."
  Goto done_autostart

  ExecWait '"$SYSDIR\schtasks.exe" /Create /TN "${AUTOSTART_TASK_NAME}" /SC ONLOGON /TR "$\"$INSTDIR\main.exe$\"" /RL HIGHEST /F' $0
  IntCmp $0 0 done_autostart

  DetailPrint "Autostart task creation with HIGHEST privileges failed (exit code: $0). Retrying with LIMITED privileges..."
  ExecWait '"$SYSDIR\schtasks.exe" /Create /TN "${AUTOSTART_TASK_NAME}" /SC ONLOGON /TR "$\"$INSTDIR\main.exe$\"" /RL LIMITED /F' $0
  IntCmp $0 0 done_autostart

  MessageBox MB_ICONEXCLAMATION|MB_OK "RePCC installed, but creating the autostart task failed (exit code: $0). You can enable it later from RePCC settings."
  DetailPrint "Autostart task creation failed with exit code: $0"

done_autostart:

SectionEnd

Section "un.Close running RePCC apps" UNSEC_CLOSE
  ExecWait '"$SYSDIR\taskkill.exe" /F /T /IM "main.exe"' $1
  ExecWait '"$SYSDIR\taskkill.exe" /F /T /IM "openfile.exe"' $1
SectionEnd

Section "un.Uninstall RePCC (required)" UNSEC_MAIN
  SectionIn RO
  ExecWait '"$SYSDIR\schtasks.exe" /Delete /TN "${AUTOSTART_TASK_NAME}" /F' $0
  StrCmp $0 0 +2
  ExecWait '"$SYSDIR\schtasks.exe" /Delete /TN "\${AUTOSTART_TASK_NAME}" /F' $0

  Delete "$INSTDIR\main.exe"
  Delete "$INSTDIR\openfile.exe"
  Delete "$INSTDIR\welcome.html"
  Delete "$INSTDIR\Uninstall.exe"

  RMDir "$INSTDIR"

  DeleteRegKey HKCR ".pcmac"
  DeleteRegKey HKCR "RePCC_File"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC"
SectionEnd

Section /o "un.Remove user data in AppData (.RePCC)" UNSEC_APPDATA
  RMDir /r /REBOOTOK "$APPDATA\.RePCC"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MAIN} $(DESC_SEC_MAIN)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_OPENFILE} $(DESC_SEC_OPENFILE)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_AUTOSTART} $(DESC_SEC_AUTOSTART)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

!insertmacro MUI_UNFUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${UNSEC_CLOSE} $(DESC_UNSEC_CLOSE)
  !insertmacro MUI_DESCRIPTION_TEXT ${UNSEC_MAIN} $(DESC_UNSEC_MAIN)
  !insertmacro MUI_DESCRIPTION_TEXT ${UNSEC_APPDATA} $(DESC_UNSEC_APPDATA)
!insertmacro MUI_UNFUNCTION_DESCRIPTION_END