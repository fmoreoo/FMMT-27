; Inno Setup script for the FMMT 27 installer. "Build exe.bat" compiles it after building the exe.
; Keep AppId the same in every release: it is how a new installer finds and replaces the old version.

#define AppName "FMMT 27"
#define AppVersion "1.0.3"
#define AppExe "FMMT 27.exe"

[Setup]
AppId={{7C1F4E52-9B3A-4D6E-8A27-3E5D0F6B1C27}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
ShowLanguageDialog=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=LICENSE
SetupIconFile={#AppName}.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
CloseApplications=force
RestartApplications=no
OutputDir=dist
OutputBaseFilename={#AppName} Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
{ The reader has no window to close politely, and its Edge window would stay open with nothing behind it. }
procedure CloseTool;
var
  Code: Integer;
begin
  Exec('powershell.exe', '-NoProfile -NonInteractive -WindowStyle Hidden -Command "Get-CimInstance Win32_Process | ' +
    'Where-Object { $_.Name -eq ''FMMT 27.exe'' -or ($_.Name -eq ''msedge.exe'' -and $_.CommandLine -like ''*FMMT 27\window*'') } | ' +
    'ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Sleep(1000);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  CloseTool;
  Result := '';
end;

function InitializeUninstall(): Boolean;
begin
  CloseTool;
  Result := True;
end;

{ Settings, the shortlist and the window profile live here, apart from the program folder.
  Asked in the wizard; a silent uninstall keeps them unless /DELETEDATA=1 is passed. }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Remove: Boolean;
begin
  if CurUninstallStep <> usPostUninstall then
    exit;
  if UninstallSilent then
    Remove := ExpandConstant('{param:DELETEDATA|0}') = '1'
  else
    Remove := MsgBox('Also delete your FMMT 27 settings and shortlist?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
  if Remove then
    DelTree(ExpandConstant('{localappdata}\{#AppName}'), True, True, True);
end;
