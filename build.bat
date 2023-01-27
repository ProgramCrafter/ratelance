@echo off
cls
set BASE_DIR=%CD%
set FIFTPATH=%FIFTPATH%

echo ==========================================
toncli build
echo ====== Built contract ====================

copy %FIFTPATH%toncli\lib\fift-libs\Fift.fif Fift.fif         >nul
copy %FIFTPATH%toncli\lib\fift-libs\Asm.fif Asm.fif           >nul
copy %FIFTPATH%toncli\lib\fift-libs\AsmTests.fif AsmTests.fif >nul
copy %FIFTPATH%toncli\lib\fift-libs\TonUtil.fif TonUtil.fif   >nul
copy %FIFTPATH%toncli\lib\fift-libs\Lists.fif Lists.fif       >nul
copy %FIFTPATH%toncli\lib\fift-libs\Color.fif Color.fif       >nul

more fift\exotic.fif >>Asm.fif
more fift\exotic.fif >>AsmTests.fif

echo ====== Created links for toncli ==========

if ~%1==~noclean goto finish

toncli run_tests >%BASE_DIR%\toncli.log 2>%BASE_DIR%\toncli.err
show-log.py

echo ====== Ran tests =========================

rem PowerShell -Command "Write-Error (Read-Host)" <build\dump-prefix.fif 2>nul >>build\contract.fif
rem PowerShell -Command "Write-Host -NoNewline %BASE_DIR%" >>build\contract.fif
rem PowerShell -Command "Write-Error (Read-Host)" <build\dump-suffix.fif 2>nul >>build\contract.fif

PowerShell -Command "Write-Error (Read-Host); Write-Host -NoNewline %BASE_DIR%" <build\dump-prefix.fif 2>nul >>build\contract.fif
more build\dump-suffix.fif >>build\contract.fif

echo ====== Powershelled paths into .fif ======

rem cd /D %FIFTPATH%
toncli fift run %BASE_DIR%\build\contract.fif
rem cd /D %BASE_DIR%

dump-hex.py build\boc\contract.boc >build\boc\contract.hex
echo ====== Dumped code into .hex file ========

rem Removing absolute path from contract.fif
toncli build >nul 2>nul
del Fift.fif
del Asm.fif
del AsmTests.fif
del TonUtil.fif
del Lists.fif
del Color.fif

echo ==========================================

:finish
