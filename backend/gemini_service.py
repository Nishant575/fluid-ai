import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

class GeminiCoach:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def analyze_interview_session(self, transcript: str, session_stats: dict) -> dict:
        """
        Analyze interview session and provide AI coaching
        """
        
        prompt = f"""You are an expert interview coach. Analyze this interview practice session.

TRANSCRIPT:
{transcript}

SESSION STATISTICS:
- Duration: {session_stats.get('duration_seconds', 0)} seconds
- Total words: {session_stats.get('total_words', 0)}
- Filler count: {session_stats.get('filler_count', 0)}
- Average pace: {session_stats.get('avg_wpm', 0)} WPM
- Filler details: {session_stats.get('filler_details', {})}

Provide a comprehensive analysis in the following JSON format:

{{
  "content_quality_score": <0-10>,
  "content_feedback": "<2-3 sentences about answer quality, depth, and relevance>",
  "communication_score": <0-10>,
  "communication_feedback": "<2-3 sentences about clarity, structure, and delivery>",
  "key_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "improvement_areas": ["<improvement 1>", "<improvement 2>", "<improvement 3>"],
  "specific_suggestions": ["<actionable tip 1>", "<actionable tip 2>", "<actionable tip 3>"],
  "missing_elements": ["<what could have been added>"],
  "overall_impression": "<1-2 sentences summary>"
}}

Focus on:
1. Answer quality (not just delivery)
2. Content depth and specificity
3. Structure and organization
4. Missing key elements (metrics, examples, results)
5. Professional communication style

Be constructive and specific. Provide actionable feedback."""

        try:
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Clean up markdown if present
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            import json
            ai_analysis = json.loads(response_text)
            
            return {
                "success": True,
                "analysis": ai_analysis
            }
            
        except Exception as e:
            print(f"❌ Gemini API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis": None
            }
    
    def generate_quick_tip(self, recent_sentences: list) -> str:
        """
        Generate a quick coaching tip based on recent speech
        """
        text = ' '.join(recent_sentences[-4:])  # Last 4 sentences
        
        prompt = f"""As an interview coach, give ONE specific, actionable tip (15-20 words) based on this speech sample:

"{text}"

Focus on content quality, not just delivery. Be encouraging but specific."""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"❌ Gemini quick tip error: {e}")
            return None
