@echo off
set PYTHONPATH=%PYTHONPATH%;%cd%;%cd%/src

IF "%~1"=="" GOTO all
IF "%1"=="u" GOTO unit
IF "%1"=="i" GOTO integr
IF "%1"=="ui" GOTO all
IF "%1"=="iu" GOTO all

echo invalid parameter: choose subset of "ui"
EXIT

:all
echo running all tests
pytest %cd%\tests
EXIT

:unit
echo running unit tests
pytest %cd%\tests -m "not integr"
EXIT

:integr
echo running integration tests
pytest %cd%\tests -m "integr"
EXIT

