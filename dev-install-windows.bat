:: This will be needed for all users on Windows to have all python dependencies available
mkdir "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\"
copy "modules\blender_helpers.py" "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\"
copy "modules\skybrush_converter.py" "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\"
Xcopy /E /I /Y ".venv\Lib\site-packages\natsort" "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\natsort"

:: This will be needed for all users on Windows to have all Skybrush add-ons available
mkdir "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\addons\"
copy "addons\io_export_skybrush.py" "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\addons\"

:: This is only needed for developers with local skybrush and pyledctrl
mklink /D "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\skybrush" "d:\%USERNAME%\git\skybrush\skybrush"
mklink /D "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\pyledctrl" "d:\%USERNAME%\git\pyledctrl\src\pyledctrl"
