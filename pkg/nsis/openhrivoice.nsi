;  This file is part of OpenHRI.
;  Copyright (C) 2010  AIST-OpenHRI Project
;

!addplugindir "."

;--------------------------------
;Include Modern UI

!include "MUI.nsh"

;--------------------------------
;General

!define PACKAGE_NAME "OpenHRIVoice"
!define PACKAGE_VERSION "1.04"
!define OUTFILE "${PACKAGE_NAME}-${PACKAGE_VERSION}-installer.exe"
!define TOP_SRCDIR "..\.."
!define TOP_BUILDDIR "..\.."
!define INSTDIR_REG_ROOT "HKLM"
!define INSTDIR_REG_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}"
!define SCDIR "$SMPROGRAMS\OpenHRI\voice"

;Name and file
Name "${PACKAGE_NAME} ${PACKAGE_VERSION}"
OutFile "${OUTFILE}"
ShowInstDetails show
ShowUninstDetails show
InstallDir "$PROGRAMFILES\${PACKAGE_NAME}"
InstallDirRegKey ${INSTDIR_REG_ROOT} ${INSTDIR_REG_KEY} "InstallDir"

!include "AdvUninstLog.nsh"
!insertmacro UNATTENDED_UNINSTALL
;!insertmacro INTERACTIVE_UNINSTALL

;--------------------------------
;Interface Settings

;  !define MUI_ICON "${TOP_SRCDIR}\icons\openhrivoice.ico"
;  !define MUI_UNICON "${TOP_SRCDIR}\icons\openhrivoice.uninstall.ico"

;--------------------------------
;Pages

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE $(MUILicense)
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

;--------------------------------
;Languages

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Japanese"

;--------------------------------
;License Language String

LicenseLangString MUILicense ${LANG_ENGLISH} "${TOP_SRCDIR}\COPYING"
LicenseLangString MUILicense ${LANG_JAPANESE} "${TOP_SRCDIR}\COPYING"

;--------------------------------
;Reserve Files

;These files should be inserted before other files in the data block
;Keep these lines before any File command
;Only for solid compression (by default, solid compression is enabled for BZIP2 and LZMA)

!insertmacro MUI_RESERVEFILE_LANGDLL


;--------------------------------
;Installer Sections

Section $(TEXT_SecBase) SecBase

  SetOutPath "$INSTDIR"

  !insertmacro UNINSTALL.LOG_OPEN_INSTALL

  ; Main executables
  File "/oname=juliusrtc.exe" "${TOP_BUILDDIR}\dist\pyJuliusRTC.exe"
  File "/oname=openjtalkrtc.exe" "${TOP_BUILDDIR}\dist\pyOpenJTalkRTC.exe"
  File "/oname=festivalrtc.exe" "${TOP_BUILDDIR}\dist\pyFestivalRTC.exe"
  File "/oname=combineresultsrtc.exe" "${TOP_BUILDDIR}\dist\pyCombineResultsRTC.exe"
  File "/oname=xsltrtc.exe" "${TOP_BUILDDIR}\dist\pyXSLTRTC.exe"
  File "${TOP_BUILDDIR}\dist\srgstopls.exe"
  File "${TOP_BUILDDIR}\dist\validatesrgs.exe"
  File "${TOP_BUILDDIR}\dist\w9xpopen.exe"
  File "rtc.conf"
  File "${TOP_SRCDIR}\pyJuliusRTC\dummy.dfa"
  File "${TOP_SRCDIR}\pyJuliusRTC\dummy.dict"
  File "${TOP_SRCDIR}\pyJuliusRTC\dummy-en.dfa"
  File "${TOP_SRCDIR}\pyJuliusRTC\dummy-en.dict"
  File "${TOP_SRCDIR}\pyJuliusRTC\grammar.xsd"
  File "${TOP_SRCDIR}\pyJuliusRTC\grammar-core.xsd"
  File "${TOP_SRCDIR}\pyJuliusRTC\pls.xsd"
  File "${TOP_SRCDIR}\pyOpenJTalkRTC\windows\open_jtalk.exe"
  File "/oname=License-Open_JTalk.txt" "${TOP_SRCDIR}\pyOpenJTalkRTC\windows\COPYING"

  ; Required Libralies
  File /r "${TOP_BUILDDIR}\dist\*.pyd"
  File /r "${TOP_BUILDDIR}\dist\*.dll"
  File "${TOP_BUILDDIR}\dist\library.zip"

  ; Information/documentation files
;  File "/oname=ChangeLog.txt" "${TOP_SRCDIR}\ChangeLog"
  File "/oname=Authors.txt" "${TOP_SRCDIR}\AUTHORS"
  File "/oname=License.txt" "${TOP_SRCDIR}\COPYING"

  !insertmacro UNINSTALL.LOG_CLOSE_INSTALL

  ; tcl files
  File /r "${TOP_BUILDDIR}\dist\tcl"

  ;Store installation folder
  WriteRegStr HKLM "Software\${PACKAGE_NAME}" "" $INSTDIR

  ; Write the Windows-uninstall keys
  WriteRegStr ${INSTDIR_REG_ROOT} "${INSTDIR_REG_KEY}" "DisplayName" "${PACKAGE_NAME}"
  WriteRegStr ${INSTDIR_REG_ROOT} "${INSTDIR_REG_KEY}" "DisplayVersion" "${PACKAGE_VERSION}"
  WriteRegStr ${INSTDIR_REG_ROOT} "${INSTDIR_REG_KEY}" "Publisher" "AIST-OpenHRI Project"
  WriteRegStr ${INSTDIR_REG_ROOT} "${INSTDIR_REG_KEY}" "InstallDir" "$INSTDIR"
  WriteRegStr ${INSTDIR_REG_ROOT} "${INSTDIR_REG_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}" "NoRepair" 1

  ;Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"

  ;Create shortcuts
  CreateDirectory "${SCDIR}"
  CreateShortCut "${SCDIR}\Uninstall Voice Components.lnk" "$INSTDIR\uninstall.exe"
  CreateShortCut "${SCDIR}\juliusrtc.lnk" "$INSTDIR\juliusrtc.exe" "--gui"
  CreateShortCut "${SCDIR}\srgstopls.lnk" "$INSTDIR\srgstopls.exe" "--gui"
  CreateShortCut "${SCDIR}\validatesrgs.lnk" "$INSTDIR\validatesrgs.exe" "--gui"
  CreateShortCut "${SCDIR}\openjtalkrtc.lnk" "$INSTDIR\openjtalkrtc.exe"
  CreateShortCut "${SCDIR}\festivalrtc.lnk" "$INSTDIR\festivalrtc.exe"
  CreateShortCut "${SCDIR}\combineresultsrtc.lnk" "$INSTDIR\combineresultsrtc.exe"
  CreateShortCut "${SCDIR}\xsltrtc.lnk" "$INSTDIR\xsltrtc.exe" "--gui"

  ; download external data
  IfFileExists "$INSTDIR\downloads" +2
    CreateDirectory "$INSTDIR\downloads"

  ; julius for windows and acoustic model for japansese
  IfFileExists "$INSTDIR\downloads\julius-dictation-kit-v4.0-win.zip" +2
    NSISdl::download "http://sourceforge.jp/frs/redir.php?m=iij&f=%2Fjulius%2F44943%2Fdictation-kit-v4.0-win.zip" "$INSTDIR\downloads\julius-dictation-kit-v4.0-win.zip"
  ZipDLL::extractall "$INSTDIR\downloads\julius-dictation-kit-v4.0-win.zip" "$INSTDIR\3rdparty"

  ; julius acoustic model for english
  IfFileExists "$INSTDIR\downloads\julius-voxforge-build726.zip" +2
    NSISdl::download "http://www.repository.voxforge1.org/downloads/Main/Tags/Releases/0_1_1-build726/Julius_AcousticModels_16kHz-16bit_MFCC_O_D_(0_1_1-build726).zip" "$INSTDIR\downloads\julius-voxforge-build726.zip"
  ZipDLL::extractall "$INSTDIR\downloads\julius-voxforge-build726.zip" "$INSTDIR\3rdparty\julius-voxforge-build726"

  ; Open JTalk dictionary
  IfFileExists "$INSTDIR\downloads\open_jtalk_dic_utf_8-1.00.tar.gz" +2
    NSISdl::download "http://downloads.sourceforge.net/project/open-jtalk/Dictionary/open_jtalk_dic-1.00/open_jtalk_dic_utf_8-1.00.tar.gz?use_mirror=iij"  "$INSTDIR\downloads\open_jtalk_dic_utf_8-1.00.tar.gz"
  untgz::extract -d "$INSTDIR\3rdparty" "$INSTDIR\downloads\open_jtalk_dic_utf_8-1.00.tar.gz"

  ; Open JTalk acoustic model
  IfFileExists "$INSTDIR\downloads\hts_voice_nitech_jp_atr503_m001-1.01.tar.gz" +2
    NSISdl::download "http://downloads.sourceforge.net/project/open-jtalk/HTS%20voice/hts_voice_nitech_jp_atr503_m001-1.01/hts_voice_nitech_jp_atr503_m001-1.01.tar.gz?use_mirror=iij"  "$INSTDIR\downloads\hts_voice_nitech_jp_atr503_m001-1.01.tar.gz"
  untgz::extract -d "$INSTDIR\3rdparty" "$INSTDIR\downloads\hts_voice_nitech_jp_atr503_m001-1.01.tar.gz"

  ; Festival
  IfFileExists "$INSTDIR\downloads\festival-1.96.03-win.zip" +2
    NSISdl::download "http://downloads.sourceforge.net/project/e-guidedog/related%20third%20party%20software/0.3/festival-1.96.03-win.zip?use_mirror=iij"  "$INSTDIR\downloads\festival-1.96.03-win.zip"
  ZipDLL::extractall "$INSTDIR\downloads\festival-1.96.03-win.zip" "$INSTDIR\3rdparty\festival-1.96.03-win"

SectionEnd

;--------------------------------
;Installer Functions

Function .onInit
  !insertmacro MUI_LANGDLL_DISPLAY
  !insertmacro UNINSTALL.LOG_PREPARE_INSTALL
FunctionEnd

Function .onInstSuccess
  !insertmacro UNINSTALL.LOG_UPDATE_INSTALL
FunctionEnd

;--------------------------------
;Descriptions

  ;Language strings
  LangString TEXT_SecBase ${LANG_ENGLISH} "Standard installation."
  LangString DESC_SecBase ${LANG_ENGLISH} "Standard installation."
 
  LangString TEXT_SecBase ${LANG_JAPANESE} "Standard installation"
  LangString DESC_SecBase ${LANG_JAPANESE} "Standard installation"
 
  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecBase} $(DESC_SecBase)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END


;--------------------------------
;Uninstaller Section

Section "Uninstall"

  ;!insertmacro UNINSTALL.LOG_BEGIN_UNINSTALL
  !insertmacro UNINSTALL.LOG_UNINSTALL "$INSTDIR"
  !insertmacro UNINSTALL.LOG_END_UNINSTALL

  RMDir /r "$INSTDIR\tcl"
  RMDir /r "$INSTDIR\3rdparty"

  Delete "$INSTDIR\uninstall.exe"

  Delete "${SCDIR}\Uninstall Voice Components.lnk"
  Delete "${SCDIR}\juliusrtc.lnk"
  Delete "${SCDIR}\srgstopls.lnk"
  Delete "${SCDIR}\validatesrgs.lnk"
  Delete "${SCDIR}\openjtalkrtc.lnk"
  Delete "${SCDIR}\festivalrtc.lnk"
  Delete "${SCDIR}\combineresultsrtc.lnk"
  Delete "${SCDIR}\xsltrtc.lnk"
  RMDir "${SCDIR}"

  DeleteRegKey /ifempty ${INSTDIR_REG_ROOT} "${INSTDIR_REG_KEY}"

  ; Unregister with Windows' uninstall system
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}"

SectionEnd

;--------------------------------
;Uninstaller Functions

Function un.onInit
  !insertmacro MUI_UNGETLANGUAGE
  !insertmacro UNINSTALL.LOG_BEGIN_UNINSTALL
FunctionEnd