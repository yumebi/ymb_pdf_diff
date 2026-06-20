; Inno Setup スクリプト。事前に scripts/build.py で dist/YMB PDF DIFF/ を生成しておくこと。
; AppVersion はymb_pdf_diff/__init__.pyの__version__と合わせること。
; コード署名は行わない(SPEC.md 6章の決定事項)。

#define AppName "YMB PDF DIFF"
#define AppVersion "0.1.3"
#define DistDir "..\..\dist\YMB PDF DIFF"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=.
OutputBaseFilename=YMB_PDF_DIFF_Setup
SetupIconFile=..\..\assets\icon.ico
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=yes

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppName}.exe"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppName}.exe"

[Run]
Filename: "{app}\{#AppName}.exe"; Description: "起動する"; Flags: nowait postinstall skipifsilent
