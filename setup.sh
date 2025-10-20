#!/bin/bash

# EUNACOM Quiz App - Quick Setup Script
# Run this after cloning/creating the project

echo "🏥 EUNACOM Quiz App - Setup"
echo "=========================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "⬇️  Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Make sure you have 'questions.json' in the root directory"
echo "   (Use sample_questions.json as a template)"
echo ""
echo "2. Run the app:"
echo "   source venv/bin/activate  # Activate virtual environment"
echo "   streamlit run app.py"
echo ""
echo "3. Open browser at: http://localhost:8501"
echo ""
echo "4. Login with:"
echo "   - maria / eunacom2024"
echo "   - amigo1 / pass123"
echo "   - amigo2 / pass456"
echo ""
echo "🚀 Happy studying!"