@ECHO OFF

set OSGEO4W_ROOT=C:\OSGeo4W

set PATH=%OSGEO4W_ROOT%\bin;%PATH%
set PATH=%PATH%;%OSGEO4W_ROOT%\apps\qgis\bin
set UI_DIR=.\fieldworkimport\resources\ui
set GENERATED_DIR=C:\Users\jlong\Development\dmse\qgis\fieldworkimport\fieldworkimport\ui\generated

@echo off
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
call "%OSGEO4W_ROOT%\bin\qt5_env.bat"
call "%OSGEO4W_ROOT%\bin\py3_env.bat"
@echo off
path %OSGEO4W_ROOT%\apps\qgis-dev\bin;%OSGEO4W_ROOT%\apps\grass\grass-7.2.2\lib;%OSGEO4W_ROOT%\apps\grass\grass-7.2.2\bin;%PATH%

cd %UI_DIR%

@ECHO off

for %%f in (*.ui) do (
   echo %%~nf
   pyuic5 "%%~nf.ui" -o "%GENERATED_DIR%\%%~nf.py"
)

@REM ::Ui Compilation
@REM call pyuic5 dialog.ui -o gui\generated\ui_dialog.py

@REM ::Resources
@REM call pyrcc5 ui\resources.qrc -o gui\generated\resources_rc.py

@ECHO OFF
GOTO END

:ERROR
   echo "Failed!"
   set ERRORLEVEL=%ERRORLEVEL%
   pause

:END
@ECHO ON
