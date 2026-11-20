; Inno-Setup-Skript fuer UPA-Analyzer-Control
; Wird von .github/workflows/windows-installer.yml aufgerufen:
;   ISCC.exe /DAppVersion=0.8.3 packaging\installer.iss
; Erwartet den PyInstaller-Ordner dist\UPA-Analyzer-Control\

#define AppName "UPA-Analyzer-Control"
#define AppExe  "UPA-Analyzer-Control.exe"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
; AppId nie aendern - daran erkennt Windows Updates der gleichen Software
AppId={{B26BF95B-8889-409B-8503-05B933A3ECC5}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Vintage Audio Repair Magdeburg
AppPublisherURL=https://github.com/techniker67/UPA3-ANALYZER-CONTROL
AppSupportURL=https://github.com/techniker67/UPA3-ANALYZER-CONTROL/issues
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; ohne Administratorrechte installierbar (fuer den aktuellen Benutzer),
; auf Wunsch im Dialog fuer alle Benutzer
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
OutputDir=..\dist-installer
OutputBaseFilename={#AppName}-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\assets\icon.ico
UninstallDisplayName={#AppName} {#AppVersion}
; laufende Software vor dem Ueberschreiben schliessen lassen
CloseApplications=yes

[Languages]
Name: "german";  MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Dirs]
; Datenordner (Einstellungen, Kalibrierung, Messungen) - wird beim Deinstallieren NICHT geloescht
Name: "{userdocs}\{#AppName}"; Flags: uninsneveruninstall

[Files]
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md";    DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE";      DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";               Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExe}"; AppUserModelID: "VintageAudioRepair.UPAAnalyzerControl"
Name: "{group}\Messdaten-Ordner";          Filename: "{userdocs}\{#AppName}"
Name: "{group}\{#AppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";          Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExe}"; AppUserModelID: "VintageAudioRepair.UPAAnalyzerControl"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
