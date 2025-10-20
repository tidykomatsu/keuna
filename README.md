# 🏥 EUNACOM Quiz App

Sistema de práctica para el Examen Único Nacional de Conocimientos de Medicina (EUNACOM).

## 🚀 Quick Start

### 1. Setup Local Environment

```bash
# Clone or create project directory
mkdir eunacom-app
cd eunacom-app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Add Your Questions

Create `questions.json` in the root directory with your 2000 questions in this format:

```json
[
  {
    "question_id": "1",
    "question_number": "1",
    "topic": "Diabetes",
    "question_text": "Un paciente de 20 años...",
    "answer_options": [
      {"letter": "a.", "text": "Opción A", "is_correct": false},
      {"letter": "b.", "text": "Opción B", "is_correct": true},
      {"letter": "c.", "text": "Opción C", "is_correct": false},
      {"letter": "d.", "text": "Opción D", "is_correct": false}
    ],
    "correct_answer": "b. Opción B",
    "explanation": "Explicación detallada...",
    "source_exam": "EUNACOM 2019"
  }
]
```

### 3. Run Locally

```bash
streamlit run app.py
```

App will open at `http://localhost:8501`

### 4. Login Credentials

Default users (change in `auth.py`):
- **maria** / eunacom2024
- **amigo1** / pass123
- **amigo2** / pass456

---

## 📱 Features

- ✅ **3 Study Modes**: Random practice, topic-based, simulated exams
- ✅ **Progress Tracking**: SQLite database tracks all answers
- ✅ **Statistics Dashboard**: See accuracy by topic
- ✅ **Mobile-Friendly**: Responsive design for phones
- ✅ **Offline Capable**: Once deployed, works without internet
- ✅ **Immediate Feedback**: Explanations after each answer
- ✅ **User Accounts**: 3 separate user profiles

---

## ☁️ Deploy to Streamlit Cloud (FREE)

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/eunacom-app.git
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository: `YOUR_USERNAME/eunacom-app`
5. Main file path: `app.py`
6. Click "Deploy"

### Step 3: Share the URL

Your app will be live at: `https://YOUR_USERNAME-eunacom-app.streamlit.app`

Share this URL with your girlfriend and friends!

---

## 🔒 Change Passwords

Edit `auth.py`:

```python
valid_passwords = {
    'maria': 'NEW_PASSWORD_HERE',
    'amigo1': 'NEW_PASSWORD_HERE', 
    'amigo2': 'NEW_PASSWORD_HERE'
}
```

For production, use hashed passwords (see comments in `auth.py`).

---

## 📊 Database

The app uses SQLite (`users.db`) to track:
- User answers
- Question history
- Statistics by topic
- Overall accuracy

**Note**: On Streamlit Cloud, the database resets periodically. For persistent storage, use:
- Streamlit Secrets + Google Sheets
- PostgreSQL (Supabase free tier)
- MongoDB Atlas

---

## 🛠 File Structure

```
eunacom-app/
├── app.py                 # Main Streamlit application
├── auth.py               # Authentication logic
├── database.py           # SQLite operations
├── requirements.txt      # Python dependencies
├── questions.json        # YOUR QUESTIONS (not tracked in git)
├── .streamlit/
│   └── config.toml      # Streamlit config
├── .gitignore
└── README.md
```

---

## 🐛 Troubleshooting

### "Questions file not found"
Make sure `questions.json` exists in the root directory.

### "Module not found"
Run: `pip install -r requirements.txt`

### Database not persisting on Streamlit Cloud
Expected behavior - Streamlit Cloud resets storage. Options:
1. Accept temporary storage (fine for practice app)
2. Upgrade to persistent database (PostgreSQL, MongoDB)

### Mobile layout issues
Check `.streamlit/config.toml` exists and is properly configured.

---

## 🎯 Next Steps

**Optional Enhancements:**

1. **Persistent Database**: Migrate to Supabase (PostgreSQL)
2. **Export Results**: Add CSV download of user statistics
3. **Spaced Repetition**: Show questions user got wrong more frequently
4. **Timer**: Add countdown timer for exam mode
5. **Mobile App**: Convert to PWA for installable app
6. **Images**: Add support for questions with images/diagrams

---

## 📝 License

Personal use only - for your girlfriend and friends.

---

## 💡 Support

Questions? Check:
- [Streamlit Docs](https://docs.streamlit.io)
- [Polars Docs](https://pola-rs.github.io/polars/)

---

**Built with ❤️ for EUNACOM preparation**