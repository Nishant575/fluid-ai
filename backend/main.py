from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
from dotenv import load_dotenv
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
import time
from queue import Queue
import random
import re
import uuid
from database import SessionDatabase
from collections import Counter

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = SessionDatabase()

class SessionCoach:
    def __init__(self, session_id):
        self.session_id = session_id
        self.sentences = []
        self.sentence_count = 0
        self.checkpoint_interval = 4
        
        self.current_window_text = []
        self.window_start_time = time.time()
        self.session_start_time = time.time()
        
        self.all_fillers_found = []  # Track all fillers for summary
        self.all_words = []
        
        # Detection lists
        self.filler_phrases = ['you know', 'i mean', 'kind of', 'sort of', 'i guess']
        self.filler_words = ['um', 'uh', 'like', 'so', 'actually', 'basically', 'literally', 'yeah', 'right']
        self.weak_words = ['maybe', 'probably', 'i think', 'perhaps', 'possibly']
        self.power_words = ['achieved', 'implemented', 'developed', 'led', 'created', 
                           'solved', 'improved', 'built', 'delivered', 'designed', 
                           'managed', 'increased', 'reduced', 'optimized']
        
        self.is_paused = False
        
        # Message banks
        self.encouragement = [
            "Excellent clarity!",
            "You sound confident!",
            "Strong technical explanation!",
            "Great answer structure!",
            "Very professional tone!",
            "Well articulated!",
            "Impressive depth of knowledge!",
            "Clear and concise!",
            "You're doing great!",
            "Perfect pacing!"
        ]
        
        self.filler_feedback = [
            "Too many fillers - pause when thinking",
            "Reduce 'um', 'like', 'you know' - use pauses",
            "Watch the filler words - be more direct",
            "Try replacing fillers with brief silence"
        ]
    
    def _clean_text(self, text):
        """Remove punctuation and normalize text"""
        cleaned = re.sub(r'[^\w\s]', '', text.lower())
        cleaned = ' '.join(cleaned.split())
        return cleaned
    
    def _count_fillers(self, text):
        """Count filler words and phrases"""
        cleaned_text = self._clean_text(text)
        filler_count = 0
        found_fillers = []
        
        for phrase in self.filler_phrases:
            count = cleaned_text.count(phrase)
            if count > 0:
                filler_count += count
                found_fillers.extend([phrase] * count)
        
        for phrase in self.filler_phrases:
            cleaned_text = cleaned_text.replace(phrase, '')
        
        words = cleaned_text.split()
        for word in words:
            if word in self.filler_words:
                filler_count += 1
                found_fillers.append(word)
        
        return filler_count, found_fillers
    
    def analyze_transcript(self, text: str):
        """Collect sentences and analyze at checkpoints"""
        if not text or len(text.strip()) == 0 or self.is_paused:
            return None
        
        self.sentences.append(text)
        self.sentence_count += 1
        self.current_window_text.append(text)
        
        # Track all words
        cleaned = self._clean_text(text)
        self.all_words.extend(cleaned.split())
        
        print(f"📝 Sentence {self.sentence_count}: {text}")
        
        if self.sentence_count % self.checkpoint_interval == 0:
            return self._analyze_checkpoint()
        
        return None
    
    def _analyze_checkpoint(self):
        """Analyze checkpoint window"""
        print(f"\n🔍 CHECKPOINT - Analyzing last {self.checkpoint_interval} sentences...")
        
        full_window_text = ' '.join(self.current_window_text)
        cleaned_text = self._clean_text(full_window_text)
        
        filler_count, found_fillers = self._count_fillers(full_window_text)
        self.all_fillers_found.extend(found_fillers)  # Track for summary
        
        total_words = len(cleaned_text.split())
        window_duration = time.time() - self.window_start_time
        wpm = (total_words / window_duration * 60) if window_duration > 0 else 0
        
        weak_count = sum(1 for phrase in self.weak_words if phrase in cleaned_text)
        words = cleaned_text.split()
        power_count = sum(1 for word in words if word in self.power_words)
        
        print(f"   Words: {total_words} | Fillers: {filler_count} {found_fillers} | WPM: {wpm:.0f} | Power: {power_count}")
        
        feedback = None
        
        # Feedback logic (same as before)
        if filler_count >= 4:
            feedback = {"type": "warning", "message": random.choice(self.filler_feedback)}
        elif weak_count >= 2:
            feedback = {"type": "warning", "message": "Be more assertive - avoid 'I think', 'maybe'"}
        elif wpm > 190:
            feedback = {"type": "warning", "message": "Slow down - take your time to breathe"}
        elif filler_count >= 2:
            feedback = {"type": "info", "message": f"Noticed {filler_count} fillers - try pausing instead"}
        elif wpm > 170:
            feedback = {"type": "info", "message": "Pace is a bit quick - you can slow down"}
        elif wpm < 90 and total_words > 10:
            feedback = {"type": "info", "message": "Pick up the pace - add more energy"}
        elif power_count >= 2:
            feedback = {"type": "success", "message": random.choice([
                "Strong action-oriented language!", "Excellent professional vocabulary!", "Great use of impactful words!"
            ])}
        elif filler_count <= 1:
            feedback = {"type": "success", "message": random.choice([
                "Excellent clarity - minimal fillers!", "Very articulate and clear!", "Clean and professional delivery!"
            ])}
        elif 110 <= wpm <= 160:
            feedback = {"type": "success", "message": random.choice([
                "Perfect pacing - keep it up!", "Great speaking speed!", "Excellent rhythm and flow!"
            ])}
        else:
            feedback = {"type": "success", "message": random.choice(self.encouragement)}
        
        print(f"💬 Feedback: [{feedback['type']}] {feedback['message']}\n")
        
        self.current_window_text = []
        self.window_start_time = time.time()
        
        return feedback
    
    def get_session_summary(self):
        """Generate comprehensive session summary"""
        duration = int(time.time() - self.session_start_time)
        total_words = len(self.all_words)
        avg_wpm = (total_words / (duration / 60)) if duration > 0 else 0
        
        # Count filler breakdown
        filler_counter = Counter(self.all_fillers_found)
        filler_details = dict(filler_counter.most_common())
        total_fillers = sum(filler_counter.values())
        
        # Calculate confidence score (0-100)
        filler_penalty = min(total_fillers * 3, 40)
        pace_bonus = 10 if 110 <= avg_wpm <= 160 else 0
        confidence_score = max(60 - filler_penalty + pace_bonus, 0)
        
        # Determine strengths
        strengths = []
        if total_fillers <= 5:
            strengths.append("Clean and articulate speech")
        if 110 <= avg_wpm <= 160:
            strengths.append("Perfect pacing")
        if self.sentence_count >= 10:
            strengths.append("Good session length")
        
        # Determine improvements
        improvements = []
        if total_fillers > 8:
            most_common_filler = filler_counter.most_common(1)[0][0] if filler_counter else "fillers"
            improvements.append(f"Reduce '{most_common_filler}' usage")
        if avg_wpm > 170:
            improvements.append("Slow down your pace")
        elif avg_wpm < 100:
            improvements.append("Increase energy and pace")
        
        return {
            "duration_seconds": duration,
            "total_words": total_words,
            "total_sentences": self.sentence_count,
            "filler_count": total_fillers,
            "filler_details": filler_details,
            "avg_wpm": round(avg_wpm, 1),
            "confidence_score": confidence_score,
            "strengths": strengths if strengths else ["Keep practicing!"],
            "improvements": improvements if improvements else ["You're doing great!"],
            "full_transcript": ' '.join(self.sentences)
        }

@app.get("/")
async def root():
    return {"status": "EchoMind - Session Management Active", "version": "2.4"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ Desktop app connected")
    
    session_id = str(uuid.uuid4())
    coach = None
    feedback_queue = Queue()
    is_running = True
    
    async def feedback_sender():
        while is_running:
            try:
                if not feedback_queue.empty():
                    feedback = feedback_queue.get_nowait()
                    if feedback is not None:
                        await websocket.send_json(feedback)
                
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Error sending feedback: {e}")
                break
    
    sender_task = asyncio.create_task(feedback_sender())
    
    try:
        deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
        dg_connection = deepgram.listen.live.v("1")
        
        def on_message(self, result, **kwargs):
            if coach and not coach.is_paused:
                sentence = result.channel.alternatives[0].transcript
                if len(sentence) > 0:
                    feedback = coach.analyze_transcript(sentence)
                    if feedback:
                        feedback_queue.put({"type": "FEEDBACK", "data": feedback})
        
        def on_error(self, error, **kwargs):
            print(f"❌ Deepgram error: {error}")
        
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)
        
        options = LiveOptions(
            model="nova-2",
            language="en-US",
            smart_format=True,
            encoding="linear16",
            channels=1,
            sample_rate=16000,
            interim_results=False
        )
        
        if not dg_connection.start(options):
            await websocket.close()
            return
        
        print("🎤 Ready for session commands\n")
        
        try:
            while True:
                data = await websocket.receive()
                
                # Handle control commands
                if 'text' in data:
                    message = json.loads(data['text'])
                    
                    if message['type'] == 'START_SESSION':
                        coach = SessionCoach(session_id)
                        db.create_session(session_id)
                        print(f"▶️ Session started: {session_id}")
                        await websocket.send_json({
                            "type": "SESSION_STARTED",
                            "session_id": session_id
                        })
                    
                    elif message['type'] == 'PAUSE_SESSION':
                        if coach:
                            coach.is_paused = True
                            print("⏸️ Session paused")
                            await websocket.send_json({"type": "SESSION_PAUSED"})
                    
                    elif message['type'] == 'RESUME_SESSION':
                        if coach:
                            coach.is_paused = False
                            print("▶️ Session resumed")
                            await websocket.send_json({"type": "SESSION_RESUMED"})
                    
                    elif message['type'] == 'END_SESSION':
                        if coach:
                            summary = coach.get_session_summary()
                            db.end_session(session_id, summary)
                            print(f"⏹️ Session ended: {session_id}\n")
                            await websocket.send_json({
                                "type": "SESSION_SUMMARY",
                                "summary": summary
                            })
                            coach = None
                
                # Handle audio data
                elif 'bytes' in data and coach and not coach.is_paused:
                    audio_data = data['bytes']
                    dg_connection.send(audio_data)
                    
        except WebSocketDisconnect:
            print("❌ Desktop app disconnected")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            is_running = False
            sender_task.cancel()
            try:
                await sender_task
            except asyncio.CancelledError:
                pass
            dg_connection.finish()
            
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    print("🚀 EchoMind - Phase 2A: Session Management")
    print("📡 WebSocket: ws://localhost:8000/ws")
    print("🎯 Features: Start/Pause/End + Summary + Database\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)