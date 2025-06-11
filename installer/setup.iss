; Inno Setup Script for Ultimate Image Compressor
; This script expects a define 'AppRoot' passed from the command line.

#ifndef AppRoot
  #error "This script must be compiled via the build.bat script."
#endif

[Setup]
AppId={{C1A8A331-B6E7-4E8F-8E5A-A7E08249F278}}
AppName=Ultimate Image Compressor
AppVersion=1.4.0
AppPublisher=Pro-Coder-Boy
PrivilegesRequired=admin
DefaultDirName={autopf}\UltimateImageCompressor
DefaultGroupName=Ultimate Image Compressor
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Use the defined AppRoot to create absolute paths
OutputDir={#AppRoot}\InstallerOutput
OutputBaseFilename=Setup-ImageCompressor-v1.4.0
SetupIconFile={#AppRoot}\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";
Name: "sendtoicon"; Description: "Add shortcut to 'Send To' menu"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
; Source path now uses the robust AppRoot define
Source: "{#AppRoot}\dist\compressor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Ultimate Image Compressor"; Filename: "{app}\compressor.exe"
Name: "{group}\{cm:UninstallProgram,Ultimate Image Compressor}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Ultimate Image Compressor"; Filename: "{app}\compressor.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Windows\SendTo\Image Compressor"; Filename: "{app}\compressor.exe"; Tasks: sendtoicon;

[Run]
Filename: "{app}\compressor.exe"; Description: "{cm:LaunchProgram,Ultimate Image Compressor}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCR; Subkey: "Applications\compressor.exe"; Flags: uninsdeletekey
Root: HKCR; Subkey: "Applications\compressor.exe\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\compressor.exe"" --shift ""%1"""
Root: HKCR; Subkey: ".jpeg\OpenWithProgids"; ValueType: string; ValueName: "ImageCompressor.File"; Flags: uninsdeletevalue
Root: HKCR; Subkey: ".jpg\OpenWithProgids"; ValueType: string; ValueName: "ImageCompressor.File"; Flags: uninsdeletevalue
Root: HKCR; Subkey: ".png\OpenWithProgids"; ValueType: string; ValueName: "ImageCompressor.File"; Flags: uninsdeletevalue
Root: HKCR; Subkey: ".webp\OpenWithProgids"; ValueType: string; ValueName: "ImageCompressor.File"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "ImageCompressor.File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "ImageCompressor.File\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\compressor.exe,0"
Root: HKCR; Subkey: "ImageCompressor.File\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\compressor.exe"" --shift ""%1"""
