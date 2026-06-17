; Script de Inno Setup para el Simulador Industrial OpenTP
; ¡Genera un único instalador profesional con accesos directos automáticos!

[Setup]
AppName=OpenTP
AppVersion=1.0
AppPublisher=Asociación Open Source
DefaultDirName={autopf}\OpenTP
DefaultGroupName=OpenTP
AllowNoIcons=yes

; Ruta donde quieres que se guarde el instalador final terminado (Se creará en tu Escritorio)
OutputDir={userdesktop}
OutputBaseFilename=Instalador_OpenTP

; Icono oficial que tendrá el archivo ejecutable del instalador
SetupIconFile=C:\Users\moren\Documents\OpenTP\src\assets\icons\icon_OpenTP.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 1. Vincula tu ejecutable principal compilado por PyInstaller
Source: "C:\Users\moren\Documents\OpenTP\dist\main\main.exe"; DestDir: "{app}"; Flags: ignoreversion; DestName: "OpenTP.exe"

; 2. Vincula absolutamente todas las librerías, subcarpetas (_internal) y assets de la distribución
Source: "C:\Users\moren\Documents\OpenTP\dist\main\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Configuración de los accesos directos automáticos en Windows con tu icono naranja
Name: "{group}\OpenTP"; Filename: "{app}\OpenTP.exe"; IconFilename: "{app}\src\assets\icons\icon_OpenTP.ico"
Name: "{commondesktop}\OpenTP"; Filename: "{app}\OpenTP.exe"; Tasks: desktopicon; IconFilename: "{app}\src\assets\icons\icon_OpenTP.ico"

[Run]
; Casilla final opcional para ejecutar el simulador inmediatamente al terminar la instalación
Filename: "{app}\OpenTP.exe"; Description: "{cm:LaunchProgram,OpenTP Simulator}"; Flags: nowait postinstall skipifsilent