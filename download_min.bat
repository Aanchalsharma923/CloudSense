@echo off
setlocal enabledelayedexpansion

set URL=https://www.imdpune.gov.in/cmpg/Griddata/mintemp.php
set OUT_DIR=.\data

if not exist "%OUT_DIR%" (
    mkdir "%OUT_DIR%"
)

echo Starting downloads for min temp years 2000 to 2013...

for /L %%Y in (2000,1,2013) do (
    echo Downloading min temp year %%Y...
    curl.exe -s --retry 5 --retry-connrefused -o "%OUT_DIR%\Mintemp_MinT_%%Y.GRD" -d "mintemp=%%Y" "%URL%"
    echo Finished %%Y
)

echo All downloads completed.
