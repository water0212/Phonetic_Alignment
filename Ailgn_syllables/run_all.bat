@echo off
echo ==========================================
echo Starting Process...
echo ==========================================

echo [1/8] Running Script 1...
py Syllable_decomposition01.py
if %errorlevel% neq 0 goto error

echo [2/8] Running Script 2...
py Syllable_dictionary02.py
if %errorlevel% neq 0 goto error

echo [3/8] Running Phonetic_Alignment.py...
py Align_syllables03.py
if %errorlevel% neq 0 goto error

echo [4/8] Running Script 4...
py ../04Phonetic_Alignment.py
if %errorlevel% neq 0 goto error
echo [5/8] Running Script 5...
py ../vote.py
if %errorlevel% neq 0 goto error
echo [6/8] Running Script 6...
py ../Global_Statistics.py
if %errorlevel% neq 0 goto error
echo [7/8] Running Script 7...
py ../vote_result/calculate_scores_and_merge.py
if %errorlevel% neq 0 goto error
echo [8/8] Running Script 8...
py ../vote_result/json_to_excel.py
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
