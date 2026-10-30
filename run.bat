@echo off
echo ========================================================
echo        SafePlate AI - Build for a Friend
echo   Zero-Hallucination Meal Planner ^& Allergy Shield
echo ========================================================
echo.
echo Starting SafePlate AI local backend server on port 8082...
start http://localhost:8082
python backend/app.py 8082
pause
