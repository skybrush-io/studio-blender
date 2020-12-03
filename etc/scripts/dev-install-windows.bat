cd %~dp0
cd ..
cd ..

:: This will be needed for all users on Windows to have all local python dependencies available
mkdir "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\"
copy "modules\blender_helpers.py" "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\"
copy "modules\skybrush_classes.py" "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\"
copy "modules\skybrush_utils.py" "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\"

:: These are the external dependencies that are copied to the vendor folder
call poetry export -f requirements.txt -o "requirements.txt" --without-hashes
call pip install -r "requirements.txt" -t "c:\\Users\\%USERNAME%\\AppData\\Roaming\\Blender Foundation\\Blender\\2.83\\scripts\\vendor\\skybrush\\"

:: This will be needed for all users on Windows to have all Skybrush add-ons available
mkdir "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\addons\"
copy "addons\io_export_skybrush.py" "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\addons\"
copy "addons\io_import_skybrush.py" "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\addons\"

::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: This partis only needed for developers with local skybrush, pyledctrl and flockwave-logger
mkdir "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush"
mklink /D "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\skybrush" "d:\%USERNAME%\git\skybrush\skybrush"
mklink /D "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\pyledctrl" "d:\%USERNAME%\git\pyledctrl\src\pyledctrl"
:: ugly: add skybrush dependency flockwave-logger and its external dependencies
mkdir "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\flockwave"
mklink /D "c:\Users\%USERNAME%\AppData\Roaming\Blender Foundation\Blender\2.83\scripts\vendor\skybrush\flockwave\logger" "d:\%USERNAME%\git\flockwave-logger\src\flockwave\logger"
call pip install colorlog -t "c:\\Users\\%USERNAME%\\AppData\\Roaming\\Blender Foundation\\Blender\\2.83\\scripts\\vendor\\skybrush\\"
call pip install hexdump -t "c:\\Users\\%USERNAME%\\AppData\\Roaming\\Blender Foundation\\Blender\\2.83\\scripts\\vendor\\skybrush\\"
