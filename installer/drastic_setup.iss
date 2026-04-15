; ============================================================
;  DRASTIC Planner — Inno Setup installer script
;  Compile with:  build.bat  (calls ISCC.exe automatically)
;  Output:        installer\Output\DRASTIC_Planner_Setup.exe
; ============================================================

#define AppName      "DRASTIC Planner"
#define AppVersion   "1.0.0"
#define AppPublisher "Michael Blake Donaldson"
#define AppExeName   "DRASTIC.exe"
#define SourceDir    "..\dist\DRASTIC"

#ifexist "..\assets\icon.ico"
  #define SetupIconPath "..\assets\icon.ico"
#endif

[Setup]
AppId={{A3D7F2C1-84B0-4E5A-9F1D-2C8B3E6A7D05}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/Michael-Blake-Donaldson
AppSupportURL=https://github.com/Michael-Blake-Donaldson/Drastic
AppUpdatesURL=https://github.com/Michael-Blake-Donaldson/Drastic
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=DRASTIC_Planner_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
MinVersion=10.0.17763
DisableProgramGroupPage=yes
DisableDirPage=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes
ShowLanguageDialog=no
#ifdef SetupIconPath
SetupIconFile={#SetupIconPath}
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "Create a &desktop shortcut";       GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Pin to &taskbar on first launch"; GroupDescription: "Additional shortcuts:"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; Main application bundle (everything PyInstaller produced)
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"; Comment: "Humanitarian scenario planning"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

; Desktop (optional — user-selected)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch the app after installation completes
Filename: "{app}\{#AppExeName}"; \
    Description: "Launch {#AppName} now"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Nothing in AppData is removed — user data (scenarios, exports) is preserved intentionally.
; If you want a clean uninstall, add lines here pointing at {userappdata}\Drastic.

[Code]
// ---------------------------------------------------------------------------
// Prevent installing an older version over a newer one.
// ---------------------------------------------------------------------------
function InitializeSetup(): Boolean;
var
  InstalledVersion: String;
begin
  Result := True;
  if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A3D7F2C1-84B0-4E5A-9F1D-2C8B3E6A7D05}_is1',
                         'DisplayVersion', InstalledVersion) then
  begin
    if CompareStr(InstalledVersion, '{#AppVersion}') > 0 then
    begin
      MsgBox('A newer version (' + InstalledVersion + ') of {#AppName} is already installed.'
             + #13#10 + 'Setup will now exit.', mbInformation, MB_OK);
      Result := False;
    end;
  end;
end;
