; Inno Setup スクリプト。事前に scripts/build.py で dist/YMB PDF DIFF/ を生成しておくこと。
; AppVersion はymb_pdf_diff/__init__.pyの__version__と合わせること。
; コード署名は行わない(SPEC.md 6章の決定事項)。
; AppNameは表示名(画面に出る名前)、ExeName/DistDirはPyInstallerが生成する実ファイル名(技術名、固定)。

#define AppName "YMB PDF差分抽出ツール"
#define ExeName "YMB PDF DIFF.exe"
#define AppVersion "1.0.1"
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
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"

[Run]
Filename: "{app}\{#ExeName}"; Description: "起動する"; Flags: nowait postinstall skipifsilent
