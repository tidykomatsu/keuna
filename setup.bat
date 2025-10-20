@echo off
REM EUNACOM Quiz App - Quick Setup Script for Windows

echo 🏥 EUNACOM Quiz App - Setup
echo ==========================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python found
python --version
echo.

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔌 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo ⬇️  Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ✅ Setup complete!
echo.
echo 📝 Next steps:
echo 1. Make sure you have 'questions.json' in the root directory
echo    (Use sample_questions.json as a template)
echo.
echo 2. Run the app:
echo    venv\Scripts\activate.bat
echo    streamlit run app.py
echo.
echo 3. Open browser at: http://localhost:8501
echo.
echo 4. Login with:
echo    - maria / eunacom2024
echo    - amigo1 / pass123
echo    - amigo2 / pass456
echo.
echo 🚀 Happy studying!
echo.
pause