# 🚀 SUPABASE MIGRATION GUIDE

Complete guide to migrating EUNACOM Quiz App from SQLite to Supabase PostgreSQL with smart question selection.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step-by-Step Migration](#step-by-step-migration)
4. [Testing](#testing)
5. [Deployment](#deployment)
6. [Troubleshooting](#troubleshooting)

## Overview

### What's Changing

**Before:**
- SQLite database (local file, not persistent on Streamlit Cloud)
- JSON file for questions (loaded from disk)
- Random question selection

**After:**
- PostgreSQL/Supabase (cloud-hosted, fully persistent)
- Questions stored in database
- Smart question selection based on user performance
- Automatic performance tracking with triggers

### What's NEW

✨ **Smart Question Selection**
- Adaptive algorithm prioritizes questions you need to review
- Tracks performance per question, per user
- Multiple selection modes: adaptive, unanswered, weakest, random

✨ **Automatic Performance Tracking**
- Database triggers automatically update performance stats
- Priority scoring system
- Streak tracking for consecutive correct answers

✨ **Persistent Data**
- All data survives Streamlit Cloud restarts
- No data loss between deployments
- Secure cloud storage

## Prerequisites

### 1. Supabase Account

1. Go to [https://supabase.com](https://supabase.com)
2. Sign up for free account
3. Create a new project
4. Note your project name and password

### 2. Get Database Connection String

1. Open your Supabase project dashboard
2. Go to **Settings** → **Database**
3. Scroll to **Connection string** section
4. Select **Connection pooling** tab
5. Copy the connection string (should start with `postgresql://`)
6. Replace `[YOUR-PASSWORD]` with your actual database password

Example:
```
postgresql://postgres.abcdefghijklmnop:MySecretPassword123@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

## Step-by-Step Migration

### Step 1: Create Database Schema

1. Open your Supabase project
2. Go to **SQL Editor**
3. Click **+ New Query**
4. Copy and paste the entire contents of `docs/SUPABASE_SCHEMA.sql`
5. Click **Run** or press `Ctrl+Enter`
6. Verify success - you should see:
   - ✅ Tables created
   - ✅ Indexes created
   - ✅ Trigger created

**Tables created:**
- `questions` - All EUNACOM questions
- `user_answers` - Every answer submitted
- `user_question_performance` - Performance stats per question
- `flashcard_reviews` - Flashcard review history
- `custom_flashcards` - User-created flashcards

### Step 2: Configure Local Environment

Create `.streamlit/secrets.toml`:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` and add your connection string:

```toml
DATABASE_URL = "postgresql://postgres.xxxxx:YOUR_PASSWORD@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
```

⚠️ **Important:** Add `.streamlit/secrets.toml` to `.gitignore` to avoid committing secrets!

```bash
echo ".streamlit/secrets.toml" >> .gitignore
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `psycopg2-binary` - PostgreSQL driver
- `python-dotenv` - Environment variable management

### Step 4: Import Questions into Database

Run the import script to load questions from JSON into Supabase:

```bash
python scripts/import_questions.py
```

This will:
1. Load questions from `EUNACOM/OUTPUTS/questions_complete_20251019_185913.json`
2. Validate each question structure
3. Extract topics from source files
4. Insert into Supabase database
5. Show success/error counts

**Expected Output:**
```
📂 Loading questions from: EUNACOM/OUTPUTS/questions_complete_20251019_185913.json
📊 Found 1500 questions
🔍 Validating and enriching question structure...
✅ Validation passed: 1450 valid questions
⚠️  Filtered out 50 invalid questions
💾 Inserting into database...
✅ Successfully inserted: 1450
❌ Errors: 0
📊 Total questions in database: 1450
```

To import a different JSON file:
```bash
python scripts/import_questions.py path/to/your/questions.json
```

### Step 5: Test Locally

```bash
streamlit run app.py
```

**Test checklist:**
- [ ] App starts without errors
- [ ] Questions load from database
- [ ] Random practice mode works
- [ ] Topic-based practice works
- [ ] Smart selection modes work (adaptive, unanswered, weakest)
- [ ] Answers are saved
- [ ] Stats update correctly
- [ ] Flashcards work
- [ ] Custom flashcards work

### Step 6: Configure Streamlit Cloud Secrets

1. Go to [https://share.streamlit.io](https://share.streamlit.io)
2. Select your app
3. Click **Settings** (⚙️)
4. Go to **Secrets** tab
5. Add your database connection:

```toml
DATABASE_URL = "postgresql://postgres.xxxxx:YOUR_PASSWORD@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
```

6. Click **Save**

### Step 7: Deploy

Commit and push all changes:

```bash
git add .
git commit -m "Migrate to Supabase with smart question selection"
git push
```

Streamlit Cloud will automatically redeploy.

## Testing

### Local Testing

**Test Database Connection:**
```python
# Test script
from src.database import init_database, get_question_count

# Test connection
success = init_database()
print(f"Connection: {'✅ Success' if success else '❌ Failed'}")

# Count questions
count = get_question_count()
print(f"Questions in database: {count}")
```

**Test Question Selection:**
```python
from src.question_selector import select_next_question

# Test adaptive selection
question = select_next_question("testuser", mode="adaptive")
print(f"Selected: {question['question_text'][:50]}...")
```

### Production Testing

After deploying to Streamlit Cloud:

1. **Verify Questions Load**
   - Navigate to "Práctica Aleatoria"
   - Questions should display immediately
   - No errors about missing database

2. **Test Answer Submission**
   - Answer a question
   - Check that stats update
   - Refresh page - stats should persist

3. **Test Smart Selection**
   - Switch between selection modes
   - Answer questions correctly → they should appear less
   - Answer incorrectly → they should appear more often

4. **Test Performance Tracking**
   - Go to "Estadísticas"
   - Verify stats by topic show correctly
   - Check that accuracy is calculated properly

## Database Operations

### View Data in Supabase

1. Go to Supabase dashboard
2. Click **Table Editor**
3. Select a table to view data:
   - `questions` - All questions
   - `user_answers` - All submitted answers
   - `user_question_performance` - Performance stats

### Run Custom Queries

Go to **SQL Editor** and run queries:

```sql
-- See all users
SELECT DISTINCT username FROM user_answers;

-- User stats
SELECT
    username,
    COUNT(*) as total_answered,
    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct,
    AVG(CASE WHEN is_correct THEN 100.0 ELSE 0.0 END) as accuracy
FROM user_answers
GROUP BY username;

-- Questions with highest error rate
SELECT
    q.question_number,
    q.topic,
    COUNT(*) as attempts,
    SUM(CASE WHEN ua.is_correct THEN 0 ELSE 1 END) as errors,
    ROUND(SUM(CASE WHEN ua.is_correct THEN 0 ELSE 1 END)::numeric / COUNT(*) * 100, 1) as error_rate
FROM questions q
JOIN user_answers ua ON q.question_id = ua.question_id
GROUP BY q.question_id, q.question_number, q.topic
HAVING COUNT(*) > 5
ORDER BY error_rate DESC
LIMIT 20;
```

## Troubleshooting

### Error: "DATABASE_URL not found"

**Cause:** Missing secrets configuration

**Fix:**
1. Local: Create `.streamlit/secrets.toml` with DATABASE_URL
2. Cloud: Add DATABASE_URL to Streamlit Cloud secrets

### Error: "relation 'questions' does not exist"

**Cause:** Database schema not created

**Fix:**
1. Go to Supabase SQL Editor
2. Run the entire `docs/SUPABASE_SCHEMA.sql` file
3. Verify tables were created in Table Editor

### Error: "No questions in database"

**Cause:** Questions not imported

**Fix:**
```bash
python scripts/import_questions.py
```

### Error: "connection refused" or timeout

**Cause:** Wrong connection string or network issue

**Fix:**
1. Verify connection string format
2. Check password is correct
3. Verify Supabase project is running
4. Try connection pooling URL (port 6543) instead of direct (port 5432)

### Questions not being selected smartly

**Cause:** Not enough performance data yet

**Fix:**
- Answer at least 10-20 questions
- The algorithm needs data to make smart selections
- Initially it will be mostly random

### Performance stats not updating

**Cause:** Database trigger not working

**Fix:**
1. Check trigger exists:
```sql
SELECT * FROM pg_trigger WHERE tgname = 'trigger_update_performance';
```

2. Recreate trigger if missing (run relevant section from SUPABASE_SCHEMA.sql)

## Data Migration (Optional)

If you have existing SQLite data you want to preserve:

### Export SQLite Data

```python
import sqlite3
import json

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Export user answers
cursor.execute("SELECT * FROM user_progress")
answers = cursor.fetchall()

# Save to JSON
with open('user_answers_backup.json', 'w') as f:
    json.dump(answers, f)
```

### Import to Supabase

```python
from src.database import save_answer
import json

with open('user_answers_backup.json', 'r') as f:
    answers = json.load(f)

for answer in answers:
    username, question_id, selected_answer, is_correct, timestamp = answer
    save_answer(username, question_id, selected_answer, bool(is_correct))
```

## Security Best Practices

### 1. Never Commit Secrets

Add to `.gitignore`:
```
.streamlit/secrets.toml
.env
*.db
__pycache__/
```

### 2. Use Environment Variables for Local Development

Alternative to secrets.toml:

```bash
export DATABASE_URL="postgresql://..."
streamlit run app.py
```

### 3. Rotate Database Password

If password is exposed:
1. Go to Supabase Settings → Database
2. Click "Reset database password"
3. Update all secrets.toml files

### 4. Enable Row Level Security (Optional)

For production apps, enable RLS in Supabase:

```sql
ALTER TABLE user_answers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only see own answers"
ON user_answers
FOR SELECT
USING (username = current_setting('app.current_user'));
```

## Performance Optimization

### 1. Connection Pooling

Already configured - we use the connection pooling URL (port 6543)

### 2. Caching

Questions are cached for 10 minutes:
```python
@st.cache_data(ttl=600)
def load_questions():
    ...
```

### 3. Indexes

All necessary indexes already created in schema:
- `idx_questions_topic` - Fast topic filtering
- `idx_user_answers_username` - Fast user lookups
- `idx_performance_priority` - Fast priority-based selection

## Monitoring

### Check App Performance

Streamlit Cloud Metrics:
1. Go to app settings
2. View "Analytics" tab
3. Monitor:
   - Active users
   - Response times
   - Error rates

### Database Monitoring

Supabase Dashboard:
1. Go to "Reports" tab
2. View:
   - Database size
   - Query performance
   - Connection count

### Set Up Alerts (Optional)

In Supabase:
1. Go to Settings → Database
2. Enable "Pooler Alerts"
3. Get notified of connection issues

## Backup and Recovery

### Automated Backups

Supabase automatically backs up your database daily.

### Manual Backup

Export entire database:
```bash
# From Supabase dashboard
# Settings → Database → Connection string
# Use direct connection (port 5432)

pg_dump -h db.xxxxx.supabase.co -U postgres -d postgres > backup.sql
```

### Restore from Backup

```bash
psql -h db.xxxxx.supabase.co -U postgres -d postgres < backup.sql
```

## What's Next?

After successful migration:

1. ✅ Monitor performance for first week
2. ✅ Gather user feedback on smart selection
3. ✅ Fine-tune priority scoring algorithm
4. ✅ Add more analytics features
5. ✅ Consider adding spaced repetition algorithm

## Support

- **Supabase Docs:** https://supabase.com/docs
- **Streamlit Docs:** https://docs.streamlit.io
- **PostgreSQL Docs:** https://www.postgresql.org/docs/

## Summary

You've successfully migrated to:
- ✅ Supabase PostgreSQL database
- ✅ Smart question selection algorithm
- ✅ Automatic performance tracking
- ✅ Persistent cloud storage
- ✅ Better user experience

**The app is now production-ready! 🎉**
