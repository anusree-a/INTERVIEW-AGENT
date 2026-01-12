"""
Agentic AI Interview Agent - FREE VERSION
Uses Groq API (Free tier: 30 requests/minute)
Alternative: Ollama (100% free, runs locally)
"""

import json
from django.conf import settings
from .models import InterviewSession, Question
from django.utils import timezone
import requests


class InterviewAgent:
    """
    Autonomous AI agent using FREE APIs
    - Primary: Groq (free tier, fast)
    - Fallback: Ollama (local, 100% free)
    """
    
    def __init__(self, session: InterviewSession):
        self.session = session
        self.use_groq = settings.USE_GROQ  # True for Groq, False for Ollama
        
        if self.use_groq:
            self.api_key = settings.GROQ_API_KEY
            self.api_url = "https://api.groq.com/openai/v1/chat/completions"
            self.model = "llama-3.3-70b-versatile"  # Free, fast, powerful
        else:
            # Ollama runs locally
            self.api_url = "http://localhost:11434/api/chat"
            self.model = "llama3.2"  # or "mistral", "phi3"
        
        # Initialize agent state if not exists
        if not self.session.agent_state:
            self.session.agent_state = {
                'current_stage': 'greeting',
                'questions_asked': 0,
                'performance_level': 'medium',
                'skill_gaps': [],
                'strong_areas': [],
            }
            self.session.save()
    
    def get_system_prompt(self):
        """Dynamic system prompt based on interview stage and context"""
        
        resume_context = ""
        if self.session.parsed_resume_data:
            resume_context = f"""
CANDIDATE RESUME SUMMARY:
- Skills: {', '.join(self.session.parsed_resume_data.get('skills', []))}
- Experience: {self.session.parsed_resume_data.get('experience_summary', 'N/A')}
- Education: {self.session.parsed_resume_data.get('education', 'N/A')}
"""
        
        cheating_context = ""
        if self.session.cheating_score > 0:
            cheating_context = f"""
ANTI-CHEATING ALERT: {self.session.cheating_score} violations detected.
Consider this in your evaluation and maintain professionalism.
"""
        
        return f"""You are an intelligent AI Interview Agent conducting a professional job interview.

CANDIDATE INFORMATION:
- Name: {self.session.candidate_name}
- Email: {self.session.email}
{resume_context}

CURRENT INTERVIEW STAGE: {self.session.agent_state.get('current_stage', 'greeting')}
QUESTIONS ASKED SO FAR: {self.session.agent_state.get('questions_asked', 0)}
PERFORMANCE LEVEL: {self.session.agent_state.get('performance_level', 'medium')}
{cheating_context}

YOUR RESPONSIBILITIES:
1. Conduct a natural, conversational interview
2. Ask relevant questions based on the current stage
3. Evaluate responses intelligently
4. Adapt difficulty based on candidate performance
5. Maintain professional and encouraging tone
6. Progress through stages: greeting → personal → resume-based → technical → closing

INTERVIEW STAGES:
- greeting: Welcome the candidate warmly, explain the process
- personal: Ask about background, motivations, career goals (2-3 questions)
- resume: Deep dive into their resume, projects, experience (3-4 questions)
- technical: Technical questions or coding logic based on role (4-5 questions)
- closing: Thank them, ask if they have questions, conclude professionally

ADAPTIVE QUESTIONING:
- If candidate struggles: Ask simpler follow-up questions, provide hints
- If candidate excels: Ask more challenging questions, probe deeper
- Always acknowledge good answers and encourage improvement

RESPONSE FORMAT - CRITICAL:
You MUST respond with ONLY a valid JSON object, no other text before or after:
{{
    "message": "Your question or response to candidate",
    "stage": "current stage name",
    "action": "ask_question|evaluate|progress_stage|conclude",
    "question_category": "PERSONAL|RESUME|TECHNICAL|BEHAVIORAL",
    "evaluation": {{
        "score": 0-10,
        "feedback": "brief feedback on their answer"
    }},
    "next_stage": "stage to move to, if progressing"
}}

IMPORTANT: Output ONLY the JSON object, nothing else. No explanations before or after.
"""
    
    def process_message(self, candidate_message: str):
        """
        Process candidate's message using FREE AI APIs
        """
        
        # Add candidate message to conversation history
        self.session.conversation_history.append({
            'role': 'user',
            'content': candidate_message,
            'timestamp': timezone.now().isoformat()
        })
        
        # Build conversation for AI
        messages = self._build_conversation_context()
        
        # Call FREE AI API
        try:
            if self.use_groq:
                response_data = self._call_groq(messages)
            else:
                response_data = self._call_ollama(messages)
            
            # Store agent response
            self.session.conversation_history.append({
                'role': 'assistant',
                'content': response_data['message'],
                'metadata': response_data,
                'timestamp': timezone.now().isoformat()
            })
            
            # Update agent state
            self._update_agent_state(response_data, candidate_message)
            
            self.session.save()
            
            return response_data
            
        except Exception as e:
            print(f"Agent error: {e}")
            return {
                'message': "I apologize for the technical difficulty. Let's continue with the interview.",
                'action': 'ask_question',
                'stage': self.session.agent_state.get('current_stage', 'greeting')
            }
    
    def _call_groq(self, messages):
        """Call Groq API (Free tier: 30 req/min, 6000 tokens/min)"""
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': self.get_system_prompt()},
                *messages
            ],
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        agent_response = result['choices'][0]['message']['content']
        
        # Parse JSON response
        return self._parse_json_response(agent_response)
    
    def _call_ollama(self, messages):
        """Call Ollama API (100% free, runs locally)"""
        
        # Build full prompt with system message
        full_messages = [
            {'role': 'system', 'content': self.get_system_prompt()},
            *messages
        ]
        
        payload = {
            'model': self.model,
            'messages': full_messages,
            'stream': False
        }
        
        response = requests.post(self.api_url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        agent_response = result['message']['content']
        
        # Parse JSON response
        return self._parse_json_response(agent_response)
    
    def _parse_json_response(self, text):
        """Extract and parse JSON from AI response"""
        try:
            # Try direct JSON parse
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            # Fallback response
            return {
                'message': text if text else "Let me ask you a question about your background.",
                'action': 'ask_question',
                'stage': self.session.agent_state.get('current_stage', 'greeting')
            }
    
    def _build_conversation_context(self):
        """Build message history for AI API"""
        messages = []
        
        # Keep last 10 messages for context (to save tokens)
        recent_history = self.session.conversation_history[-10:]
        
        for msg in recent_history:
            if msg['role'] == 'user':
                messages.append({
                    'role': 'user',
                    'content': msg['content']
                })
            elif msg['role'] == 'assistant':
                messages.append({
                    'role': 'assistant',
                    'content': msg['content']
                })
        
        return messages
    
    def _update_agent_state(self, response_data, candidate_message):
        """Update agent's internal state based on interaction"""
        
        # Update current stage
        if 'stage' in response_data:
            self.session.current_stage = response_data['stage']
            self.session.agent_state['current_stage'] = response_data['stage']
        
        # Increment question counter
        if response_data.get('action') == 'ask_question':
            self.session.agent_state['questions_asked'] += 1
        
        # Store evaluation if provided
        if 'evaluation' in response_data and response_data['evaluation']:
            eval_data = response_data['evaluation']
            
            # Create Question record
            if response_data.get('question_category'):
                # Find the last question we asked
                last_assistant_msg = None
                for msg in reversed(self.session.conversation_history):
                    if msg['role'] == 'assistant' and msg.get('metadata', {}).get('action') == 'ask_question':
                        last_assistant_msg = msg
                        break
                
                if last_assistant_msg:
                    Question.objects.create(
                        session=self.session,
                        question_text=last_assistant_msg['content'],
                        category=response_data.get('question_category', 'PERSONAL'),
                        answer_text=candidate_message,
                        answer_received_at=timezone.now(),
                        score=eval_data.get('score'),
                        feedback=eval_data.get('feedback', '')
                    )
            
            # Update performance level
            score = eval_data.get('score', 5)
            if score >= 8:
                self.session.agent_state['performance_level'] = 'high'
            elif score <= 4:
                self.session.agent_state['performance_level'] = 'low'
            else:
                self.session.agent_state['performance_level'] = 'medium'
        
        # Progress to next stage if indicated
        if response_data.get('next_stage'):
            self.session.agent_state['current_stage'] = response_data['next_stage']
            self.session.current_stage = response_data['next_stage']
        
        # Conclude interview if action is conclude
        if response_data.get('action') == 'conclude':
            self.session.complete_interview()
    
    def start_interview(self):
        """Initialize the interview with greeting"""
        self.session.start_interview()
        
        greeting_prompt = f"""Start the interview by greeting {self.session.candidate_name} warmly. 
Introduce yourself as an AI Interview Agent, explain the interview process briefly (it will have personal, 
resume-based, and technical questions), and ask your first personal question to break the ice."""
        
        return self.process_message(greeting_prompt)
    
    def generate_final_evaluation(self):
        """Generate comprehensive evaluation report"""
        
        questions = Question.objects.filter(session=self.session)
        avg_score = sum(q.score for q in questions if q.score) / max(len(questions), 1)
        
        evaluation_prompt = f"""Based on the complete interview with {self.session.candidate_name}, generate a comprehensive evaluation report.

INTERVIEW SUMMARY:
- Total Questions: {questions.count()}
- Average Score: {avg_score:.2f}/10
- Cheating Violations: {self.session.cheating_score}
- Duration: {(self.session.completed_at - self.session.started_at).seconds // 60} minutes

Provide:
1. Overall Performance Assessment (2-3 sentences)
2. Technical Skills Rating (1-10)
3. Communication Skills Rating (1-10)
4. Strengths (bullet points)
5. Areas for Improvement (bullet points)
6. Hiring Recommendation (Strong Yes / Yes / Maybe / No)

Format as a professional report.
"""
        
        messages = [{'role': 'user', 'content': evaluation_prompt}]
        
        try:
            if self.use_groq:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': 'You are an expert interviewer providing evaluation reports. Be honest and professional.'},
                        *messages
                    ],
                    'temperature': 0.7,
                    'max_tokens': 2000
                }
                
                response = requests.post(self.api_url, headers=headers, json=payload)
                result = response.json()
                evaluation_text = result['choices'][0]['message']['content']
            else:
                # Ollama
                payload = {
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': 'You are an expert interviewer providing evaluation reports.'},
                        *messages
                    ],
                    'stream': False
                }
                
                response = requests.post(self.api_url, json=payload)
                result = response.json()
                evaluation_text = result['message']['content']
            
            # Update session with evaluation
            self.session.evaluation_report = evaluation_text
            self.session.score = avg_score
            
            # Calculate specific scores
            tech_questions = questions.filter(category__in=['TECHNICAL', 'CODING'])
            if tech_questions.exists():
                self.session.technical_score = sum(q.score for q in tech_questions if q.score) / tech_questions.count()
            
            comm_questions = questions.filter(category__in=['PERSONAL', 'BEHAVIORAL'])
            if comm_questions.exists():
                self.session.communication_score = sum(q.score for q in comm_questions if q.score) / comm_questions.count()
            
            self.session.save()
            
            return evaluation_text
            
        except Exception as e:
            print(f"Evaluation generation error: {e}")
            return "Evaluation report generation failed. Please review manually."