import sqlite3
from datetime import datetime
import json

class SessionDatabase:
    def __init__(self, db_path="echomind_sessions.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration_seconds INTEGER,
                total_words INTEGER DEFAULT 0,
                total_sentences INTEGER DEFAULT 0,
                filler_count INTEGER DEFAULT 0,
                filler_details TEXT,
                avg_wpm REAL DEFAULT 0,
                confidence_score INTEGER DEFAULT 0,
                strengths TEXT,
                improvements TEXT,
                full_transcript TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized")
    
    def create_session(self, session_id):
        """Start a new session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sessions (session_id, start_time, status)
            VALUES (?, ?, 'active')
        ''', (session_id, datetime.now()))
        
        conn.commit()
        conn.close()
        print(f"📝 Session created: {session_id}")
    
    def end_session(self, session_id, session_data):
        """End a session and save final statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sessions SET
                end_time = ?,
                duration_seconds = ?,
                total_words = ?,
                total_sentences = ?,
                filler_count = ?,
                filler_details = ?,
                avg_wpm = ?,
                confidence_score = ?,
                strengths = ?,
                improvements = ?,
                full_transcript = ?,
                status = 'completed'
            WHERE session_id = ?
        ''', (
            datetime.now(),
            session_data.get('duration_seconds', 0),
            session_data.get('total_words', 0),
            session_data.get('total_sentences', 0),
            session_data.get('filler_count', 0),
            json.dumps(session_data.get('filler_details', {})),
            session_data.get('avg_wpm', 0),
            session_data.get('confidence_score', 0),
            json.dumps(session_data.get('strengths', [])),
            json.dumps(session_data.get('improvements', [])),
            session_data.get('full_transcript', ''),
            session_id
        ))
        
        conn.commit()
        conn.close()
        print(f"💾 Session saved: {session_id}")
    
    def get_all_sessions(self):
        """Get all sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM sessions ORDER BY start_time DESC
        ''')
        
        sessions = cursor.fetchall()
        conn.close()
        
        return sessions