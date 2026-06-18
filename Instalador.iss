; Script de Inno Setup para el Simulador Industrial OpenTP
; ¡Elimina versiones previas automáticamente e instala la nueva versión limpia!

[Setup]
; Identificador único del programa (Generado para OpenTP). 
; No cambies este número para que los futuros instaladores siempre reconozcan y borren las versiones anteriores.
AppId={{A8F7E4D3-6B2C-4F91-BD82-1C3A5E7F901B}
AppName=OpenTP
AppVersion=1.0
AppPublisher=Asociación Open Source
DefaultDirName={autopf}\OpenTP
DefaultGroupName=OpenTP
AllowNoIcons=yes

; --- DIRECTIVA DE REEMPLAZO DE INSTANCIAS ---
; Detecta si ya existe el programa y fuerza una instalación limpia sobreescribiendo de forma segura
MinVersion=0,6.1
DisableDirPage=auto
DisableProgramGroupPage=auto

; Configuración del archivo de salida
OutputDir={userdesktop}
OutputBaseFilename=Instalador_OpenTP
SetupIconFile=C:\Users\moren\Documents\OpenTP\src\assets\icons\icon_OpenTP.ico
; NUEVA LÍNEA: Vincula el icono al menú de aplicaciones instaladas de Windows
UninstallDisplayIcon={app}\assets\icons\icon_OpenTP.ico
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

; 2. Vincula todas las librerías, subcarpetas (_internal) y assets de la distribución
Source: "C:\Users\moren\Documents\OpenTP\dist\main\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; CORREGIDO: Rutas de los iconos alineadas a la carpeta final (Soluciona el icono blanco)
Name: "{group}\OpenTP"; Filename: "{app}\OpenTP.exe"; WorkingDir: "{app}"; IconFilename: "{app}\_internal\assets\icons\icon_OpenTP.ico"
Name: "{commondesktop}\OpenTP"; Filename: "{app}\OpenTP.exe"; WorkingDir: "{app}"; Tasks: desktopicon; IconFilename: "{app}\_internal\assets\icons\icon_OpenTP.ico"


[Run]
Filename: "{app}\OpenTP.exe"; Description: "{cm:LaunchProgram,OpenTP Simulator}"; Flags: nowait postinstall skipifsilent

; =========================================================================
; CÓDIGO INTERNO: Desinstala versiones anteriores de forma silenciosa antes de empezar
; =========================================================================
[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  UninstStr: String;
begin
  Result := True;
  // Busca en el registro de Windows si el AppId ya está registrado
  if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + ExpandConstant('{#SetupSetting("AppId")}') + '_is1', 'UninstallString', UninstStr) or
     RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + ExpandConstant('{#SetupSetting("AppId")}') + '_is1', 'UninstallString', UninstStr) then
  begin
    // Si encuentra una versión vieja, le avisa al usuario y la borra sin ventanas molestas (/SILENT)
    if MsgBox('Se detectó una versión anterior de OpenTP Simulator instalada. ¿Deseas eliminarla automáticamente para realizar una instalación limpia?', mbConfirmation, MB_YESNO) = idYes then
    begin
      // Extrae la ruta limpia de desinstalación quitando comillas
      StringChange(UninstStr, '"', '');
      if Exec(UninstStr, '/SILENT /NORESTART /SUPPRESSMSGBOXES', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
      begin
        // Espera un momento a que Windows termine de limpiar el disco duro
        Sleep(1000);
      end;
    end;
  end;
end;