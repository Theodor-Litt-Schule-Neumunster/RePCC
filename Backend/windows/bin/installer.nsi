!include MUI2.nsh

Name "RePCC"
OutFile "RePCC-Setup.exe"
InstallDir "$APPDATA\.RePCC\applications"
RequestExecutionLevel user

!define BANNER_HEADER "${__FILEDIR__}\banner.bmp"
!define BANNER_SIDE "${__FILEDIR__}\banner_welcome.bmp"

!define MUI_ICON "${__FILEDIR__}\installicon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "${BANNER_HEADER}"
!define MUI_HEADERIMAGE_UNBITMAP "${BANNER_HEADER}"
!define MUI_WELCOMEFINISHPAGE_BITMAP "${BANNER_SIDE}"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "${BANNER_SIDE}"

!define MUI_LICENSEPAGE_TEXT_TOP "Please review the GPL-3.0 license for RePCC."
!define MUI_LICENSEPAGE_TEXT_BOTTOM "A click-through acceptance is not required to receive a copy. Click Continue to proceed."
!define MUI_LICENSEPAGE_BUTTON "Continue"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.rtf"
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
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Main"
  SetOutPath "$INSTDIR"
  File "main.exe"
  File "openfile.exe"
  File "welcome.html"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "DisplayName" "RePCC"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "DisplayIcon" "$INSTDIR\main.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC" "NoRepair" 1
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\main.exe"
  Delete "$INSTDIR\openfile.exe"
  Delete "$INSTDIR\welcome.html"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\RePCC"
SectionEnd