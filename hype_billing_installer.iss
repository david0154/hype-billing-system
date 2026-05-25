; ===========================================================================
; Hype ERP v3.0.0 - Inno Setup Script
; Developer: David | Nexuzy Lab
; License:   NXL-E5AB-0B0-932 (NEXUZY Enterprise Software License)
; Website:   https://nexuzy.tech
; Developer: https://devilone.in
; Build with Inno Setup 6.x: https://jrsoftware.org/isinfo.php
; ===========================================================================

[Setup]
AppName=Hype ERP
AppVersion=3.0.0
AppVerName=Hype ERP v3.0.0
AppPublisher=Nexuzy Lab
AppPublisherURL=https://nexuzy.tech
AppSupportURL=https://github.com/david0154/hype-billing-system/issues
AppUpdatesURL=https://github.com/david0154/hype-billing-system/releases
AppCopyright=Copyright (C) 2025-2026 Nexuzy Lab. License: NXL-E5AB-0B0-932. Lead Developer: David (https://devilone.in)
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
VersionInfoVersion=3.0.0.0
VersionInfoCompany=Nexuzy Lab
VersionInfoDescription=Hype ERP - Enterprise Resource Planning System
VersionInfoCopyright=Copyright (C) 2025-2026 Nexuzy Lab
VersionInfoProductName=Hype ERP
VersionInfoProductVersion=3.0.0.0
DefaultDirName={autopf}\HypeERP
DefaultGroupName=Hype ERP
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=HypeERP_Setup_v3.0.0
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\HypeERP.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=yes
MinVersion=6.1sp1
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=auto
LicenseFile=LICENSE
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=no

[Dirs]
Name: "{localappdata}\HypeERP"
Name: "{localappdata}\HypeERP\models"
Name: "{localappdata}\HypeERP\backups"
Name: "{localappdata}\HypeERP\exports"
Name: "{localappdata}\HypeERP\logs"

[Files]
; Main EXE — installed to Program Files
Source: "dist\HypeERP.exe"; DestDir: "{app}"; Flags: ignoreversion

; Firebase encrypted key — MUST go to LOCALAPPDATA (writable, where window_utils.py looks)
Source: "serviceAccountKey.enc"; DestDir: "{localappdata}\HypeERP"; Flags: ignoreversion skipifsourcedoesntexist onlyifdoesntexist

; Firebase runtime config — also goes to LOCALAPPDATA
Source: "firebase_runtime_config.json"; DestDir: "{localappdata}\HypeERP"; Flags: ignoreversion skipifsourcedoesntexist onlyifdoesntexist

; Assets
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "logo.png"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; Documentation
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "SETUP.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Start Menu — WorkingDir ensures EXE finds its files on launch
Name: "{group}\Hype ERP"; Filename: "{app}\HypeERP.exe"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"
Name: "{group}\Uninstall Hype ERP"; Filename: "{uninstallexe}"

; Desktop shortcut — WorkingDir is critical for PyInstaller EXE
Name: "{autodesktop}\Hype ERP"; Filename: "{app}\HypeERP.exe"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
; Launch app after install — WorkingDir set so EXE starts from correct folder
Filename: "{app}\HypeERP.exe"; WorkingDir: "{app}"; Description: "Launch Hype ERP now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: dirifempty; Name: "{localappdata}\HypeERP\models"
Type: dirifempty; Name: "{localappdata}\HypeERP\backups"
Type: dirifempty; Name: "{localappdata}\HypeERP\exports"
Type: dirifempty; Name: "{localappdata}\HypeERP\logs"

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nDeveloped by David | Nexuzy Lab%nLicense: NXL-E5AB-0B0-932%n%nhttps://nexuzy.tech | https://devilone.in%n%nHype ERP is a complete offline-first GST billing and ERP system with 19 enterprise modules, AI features, and Firebase cloud sync.%n%nIt is recommended that you close all other applications before continuing.
FinishedLabel=Hype ERP v3.0.0 has been installed successfully!%n%nDefault Login: admin / admin123%nChange your password after first login.%n%nDeveloped by David | Nexuzy Lab%nhttps://nexuzy.tech | https://devilone.in

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  DataDir: String;
  SrcEnc, DstEnc: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Ensure LOCALAPPDATA\HypeERP exists
    DataDir := ExpandConstant('{localappdata}\HypeERP');
    if not DirExists(DataDir) then
      CreateDir(DataDir);

    // Safety copy: if serviceAccountKey.enc ended up in {app}, copy it to LOCALAPPDATA too
    SrcEnc := ExpandConstant('{app}\serviceAccountKey.enc');
    DstEnc := ExpandConstant('{localappdata}\HypeERP\serviceAccountKey.enc');
    if FileExists(SrcEnc) and not FileExists(DstEnc) then
      FileCopy(SrcEnc, DstEnc, False);
  end;
end;