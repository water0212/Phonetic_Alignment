@echo off
echo ==========================================
echo Starting Process...
echo ==========================================

echo [1/4] Running Script 1...
python Syllable_decomposition01.py
if %errorlevel% neq 0 goto error

echo [2/4] Running Script 2...
python Syllable_dictionary02.py
if %errorlevel% neq 0 goto error

echo [3/4] Running Phonetic_Alignment.py...
python Align_syllables03.py
if %errorlevel% neq 0 goto error

echo [4/4] Running Script 4...
python ../04Phonetic_Alignment.py
if %errorlevel% neq 0 goto error

echo ==========================================
echo All scripts finished successfully!
echo ==========================================
pause
exit

:error
echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
echo Error occurred. Process stopped.
echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
pause
