; Inno Setup Script for Ultimate Image Compressor

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{C1A8A331-B6E7-4E8F-8E5A-A7E08249F278}}
AppName=Ultimate Image Compressor
AppVersion=1.1
AppPublisher=Pro-Coder-Boy
DefaultDirName={autopf}\UltimateImageCompressor
DefaultGroupName=Ultimate Image Compressor
DisableProgramGroupPage=yes
; "architecturesallowed" specifies which architectures the setup can run on.
ArchitecturesAllowed=x64
; "compression" specifies the compression method used for the setup files.
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputDir=.\InstallerOutput
OutputBaseFilename=Setup-ImageCompressor-v1
SetupIconFile=C:\Users\myg20\OneDrive\Desktop\ImageCompressor\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";
Name: "sendtoicon"; Description: "Add shortcut to 'Send To' menu"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
; NOTE: "Source" is the folder created by PyInstaller (without --onefile)
Source: "dist\compressor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; ... all your application files will be "staged" by the installer.

[Icons]
Name: "{group}\Ultimate Image Compressor"; Filename: "{app}\compressor.exe"
Name: "{group}\{cm:UninstallProgram,Ultimate Image Compressor}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Ultimate Image Compressor"; Filename: "{app}\compressor.exe"; Tasks: desktopicon

; This is the magic line for the "Send To" shortcut
Name: "{userappdata}\Microsoft\Windows\SendTo\Image Compressor"; Filename: "{app}\compressor.exe"; Tasks: sendtoicon;

[Run]
Filename: "{app}\compressor.exe"; Description: "{cm:LaunchProgram,Ultimate Image Compressor}"; Flags: nowait postinstall skipifsilent

; --- Registry entries for "Open With" integration ---
[Registry]
; 1. Register the application itself
Root: HKCR; Subkey: "Applications\compressor.exe"; Flags: uninsdeletekey
Root: HKCR; Subkey: "Applications\compressor.exe\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\compressor.exe"" --shift ""%1"""

; 2. Associate with file types
Root: HKCR; Subkey: ".jpeg\OpenWithProgids"; ValueType: string; ValueName: "ImageCompressor.File"; Flags: uninsdeletevalue
Root: HKCR; Subkey: ".jpg\OpenWithProgids"; ValueType: string; ValueName: "ImageCompressor.File"; Flags: uninsdeletevalue
Root: HKCR; Subkey: ".png\OpenWithProgids"; ValueType: string; ValueName: "ImageCompressor.File"; Flags: uninsdeletevalue
Root: HKCR; Subkey: ".webp\OpenWithProgids"; ValueType: string; ValueName: "ImageCompressor.File"; Flags: uninsdeletevalue

; 3. Define the ProgID and its open command
Root: HKCR; Subkey: "ImageCompressor.File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "ImageCompressor.File\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\compressor.exe,0"
Root: HKCR; Subkey: "ImageCompressor.File\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\compressor.exe"" --shift ""%1"""
