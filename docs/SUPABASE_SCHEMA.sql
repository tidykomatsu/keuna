-- ============================================================================
-- SUPABASE DATABASE SCHEMA FOR EUNACOM QUIZ APP
-- ============================================================================
-- Run this SQL in your Supabase SQL Editor to create all tables
-- ============================================================================

-- ============================================================================
-- QUESTIONS TABLE - Stores all EUNACOM questions
-- ============================================================================

CREATE TABLE IF NOT EXISTS questions (
    question_id VARCHAR(50) PRIMARY KEY,
    question_number VARCHAR(10) NOT NULL,
    topic VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    answer_options JSONB NOT NULL,  -- Array of {letter, text, is_correct}
    correct_answer VARCHAR(200) NOT NULL,
    explanation TEXT NOT NULL,
    source_file VARCHAR(200),
    source_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster topic queries
CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic);
CREATE INDEX IF NOT EXISTS idx_questions_source ON questions(source_type);

-- ============================================================================
-- USER ANSWERS TABLE - Track all user responses
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_answers (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    question_id VARCHAR(50) NOT NULL REFERENCES questions(question_id),
    user_answer VARCHAR(10),
    is_correct BOOLEAN NOT NULL,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_seconds INTEGER  -- Optional: track how long user took
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_answers_username ON user_answers(username);
CREATE INDEX IF NOT EXISTS idx_user_answers_question ON user_answers(question_id);
CREATE INDEX IF NOT EXISTS idx_user_answers_user_question ON user_answers(username, question_id);

-- ============================================================================
-- USER PERFORMANCE STATS - Materialized view for fast lookups
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_question_performance (
    username VARCHAR(50) NOT NULL,
    question_id VARCHAR(50) NOT NULL REFERENCES questions(question_id),
    topic VARCHAR(100) NOT NULL,
    total_attempts INTEGER DEFAULT 0,
    correct_attempts INTEGER DEFAULT 0,
    incorrect_attempts INTEGER DEFAULT 0,
    last_answered_at TIMESTAMP,
    streak INTEGER DEFAULT 0,  -- Consecutive correct answers
    priority_score FLOAT DEFAULT 0,  -- Higher = show more often
    PRIMARY KEY (username, question_id)
);

CREATE INDEX IF NOT EXISTS idx_performance_username ON user_question_performance(username);
CREATE INDEX IF NOT EXISTS idx_performance_topic ON user_question_performance(topic);
CREATE INDEX IF NOT EXISTS idx_performance_priority ON user_question_performance(priority_score DESC);

-- ============================================================================
-- FLASHCARD REVIEWS
-- ============================================================================

CREATE TABLE IF NOT EXISTS flashcard_reviews (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    card_id VARCHAR(50) NOT NULL,
    rating VARCHAR(20) NOT NULL,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_flashcard_reviews_username ON flashcard_reviews(username);

-- ============================================================================
-- CUSTOM FLASHCARDS
-- ============================================================================

CREATE TABLE IF NOT EXISTS custom_flashcards (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    front_text TEXT NOT NULL,
    back_text TEXT NOT NULL,
    topic VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived BOOLEAN DEFAULT FALSE,
    UNIQUE(username, front_text)
);

CREATE INDEX IF NOT EXISTS idx_custom_flashcards_username ON custom_flashcards(username);

-- ============================================================================
-- TRIGGER: Update performance stats automatically
-- ============================================================================

CREATE OR REPLACE FUNCTION update_user_performance()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert or update performance record
    INSERT INTO user_question_performance (
        username,
        question_id,
        topic,
        total_attempts,
        correct_attempts,
        incorrect_attempts,
        last_answered_at,
        streak,
        priority_score
    )
    SELECT
        NEW.username,
        NEW.question_id,
        q.topic,
        1,
        CASE WHEN NEW.is_correct THEN 1 ELSE 0 END,
        CASE WHEN NEW.is_correct THEN 0 ELSE 1 END,
        NEW.answered_at,
        CASE WHEN NEW.is_correct THEN 1 ELSE 0 END,
        CASE WHEN NEW.is_correct THEN -1.0 ELSE 5.0 END  -- Wrong = high priority
    FROM questions q
    WHERE q.question_id = NEW.question_id
    ON CONFLICT (username, question_id)
    DO UPDATE SET
        total_attempts = user_question_performance.total_attempts + 1,
        correct_attempts = user_question_performance.correct_attempts +
            CASE WHEN NEW.is_correct THEN 1 ELSE 0 END,
        incorrect_attempts = user_question_performance.incorrect_attempts +
            CASE WHEN NEW.is_correct THEN 0 ELSE 1 END,
        last_answered_at = NEW.answered_at,
        streak = CASE
            WHEN NEW.is_correct THEN user_question_performance.streak + 1
            ELSE 0
        END,
        -- Priority score calculation:
        -- Higher score = show more often
        -- Wrong answers increase priority
        -- Correct streak decreases priority
        priority_score = CASE
            WHEN NEW.is_correct THEN
                GREATEST(user_question_performance.priority_score - 2.0, -10.0)
            ELSE
                LEAST(user_question_performance.priority_score + 5.0, 50.0)
        END;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger
DROP TRIGGER IF EXISTS trigger_update_performance ON user_answers;
CREATE TRIGGER trigger_update_performance
    AFTER INSERT ON user_answers
    FOR EACH ROW
    EXECUTE FUNCTION update_user_performance();
