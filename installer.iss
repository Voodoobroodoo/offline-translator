; Inno Setup script: Офлайн-переводчик 1.0.0 (per-user install, no admin)

[Setup]
AppId={{7C1A2F5E-9B34-4E7D-9C55-A1B2C3D4E5F6}
AppName=Офлайн-переводчик
AppVersion=1.0.0
AppVerName=Офлайн-переводчик 1.0.0
AppPublisher=Offline Translator Project
DefaultDirName={localappdata}\Programs\OfflineTranslator
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=release
OutputBaseFilename=Переводчик-Setup-1.0.0
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Переводчик.exe

[Tasks]
Name: "desktopicon"; Description: "Ярлык на рабочем столе"; GroupDescription: "Дополнительно:"
Name: "autostart"; Description: "Запускать при входе в Windows (для горячих клавиш)"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
Source: "dist\OfflineTranslator.exe"; DestDir: "{app}"; DestName: "Переводчик.exe"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "models_stage\packages\*"; DestDir: "{%USERPROFILE}\.local\share\argos-translate\packages"; Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall
Source: "models_stage\minisbd\*"; DestDir: "{%USERPROFILE}\.local\share\argos-translate\minisbd"; Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall

[Icons]
Name: "{autoprograms}\Офлайн-переводчик"; Filename: "{app}\Переводчик.exe"
Name: "{autodesktop}\Офлайн-переводчик"; Filename: "{app}\Переводчик.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "OfflineTranslator"; ValueData: """{app}\Переводчик.exe"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\Переводчик.exe"; Description: "Запустить Офлайн-переводчик"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
