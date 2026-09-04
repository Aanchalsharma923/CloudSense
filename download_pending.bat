@echo off
setlocal enabledelayedexpansion

set URL=https://www.imdpune.gov.in/cmpg/Griddata/rainfall.php
set OUT_DIR=.\data

if not exist "%OUT_DIR%" (
    mkdir "%OUT_DIR%"
)

echo Starting downloads for remaining years 2015 to 2025...

for /L %%Y in (2015,1,2025) do (
    echo Downloading year %%Y...
    curl.exe -s -o "%OUT_DIR%\ind%%Y_rfp25.grd" -d "rain=%%Y" "%URL%"
    echo Finished %%Y
)

echo All downloads completed.
