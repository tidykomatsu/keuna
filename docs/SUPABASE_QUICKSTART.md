# 🚀 Supabase Migration - Quick Start

## TL;DR - Get Started in 5 Minutes

### 1️⃣ Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com) → Sign up
2. Create new project (note your password!)
3. Get connection string from **Settings → Database → Connection pooling**

### 2️⃣ Run Database Schema

1. Open **SQL Editor** in Supabase
2. Copy-paste entire `docs/SUPABASE_SCHEMA.sql`
3. Click **Run** ✅

### 3️⃣ Configure Secrets

**Local:**
```bash
# Create secrets file
cat > .streamlit/secrets.toml << EOF
DATABASE_URL = "postgresql://postgres.xxxxx:YOUR_PASSWORD@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
EOF
```

**Streamlit Cloud:**
- Go to app settings → Secrets
- Paste the same DATABASE_URL

### 4️⃣ Import Questions

```bash
pip install -r requirements.txt
python scripts/import_questions.py
```

### 5️⃣ Deploy

```bash
git add .
git commit -m "Migrate to Supabase"
git push
```

## ✨ What You Get

- 🧠 **Smart Question Selection** - Prioritizes questions you need to review
- 📊 **Performance Tracking** - Automatic stats per question
- ☁️ **Cloud Storage** - All data persists forever
- 🚀 **Production Ready** - Scales automatically

## 📋 File Changes

### New Files
- `docs/SUPABASE_SCHEMA.sql` - Database schema
- `src/question_selector.py` - Smart selection algorithm
- `scripts/import_questions.py` - Question import script
- `.streamlit/secrets.toml.example` - Secrets template

### Updated Files
- `requirements.txt` - Added PostgreSQL drivers
- `src/database.py` - PostgreSQL version
- `src/utils.py` - Database-based loading
- `pages/1_📚_Practica_Aleatoria.py` - Smart selector
- `pages/2_📖_Por_Tema.py` - Smart selector

## 🎯 Selection Modes

| Mode | Description |
|------|-------------|
| 🧠 **Adaptive** | Smart mix based on performance (default) |
| 📝 **Unanswered** | Only questions you haven't answered |
| ⚠️ **Weakest** | Only questions you got wrong |
| 🎲 **Random** | Completely random selection |

## 🔍 How Smart Selection Works

1. **Track Performance** - Every answer updates priority score
2. **Calculate Weights** - Higher priority = more likely to appear
3. **Weighted Selection** - Smart probability-based picking

**Priority Scoring:**
- ✅ Correct answer → Priority -2.0 (show less)
- ❌ Wrong answer → Priority +5.0 (show more)
- 🎯 Correct streak → Priority decreases
- ⚠️ Wrong answers → Priority increases

## 🔧 Common Issues

**"DATABASE_URL not found"**
→ Add to `.streamlit/secrets.toml` or Streamlit Cloud secrets

**"No questions in database"**
→ Run `python scripts/import_questions.py`

**"relation does not exist"**
→ Run the SQL schema in Supabase SQL Editor

## 📚 Full Documentation

See `docs/MIGRATION_GUIDE.md` for complete guide.

## 🎉 You're Done!

Your app now has:
- ✅ Cloud database (Supabase)
- ✅ Smart question selection
- ✅ Automatic performance tracking
- ✅ Persistent user data

Enjoy! 🚀
