"""
Agentic AI Interview Agent
Single autonomous agent that conducts the entire interview lifecycle
"""

import json
from django.conf import settings
from .models import InterviewSession, Question
from django.utils import timezone
import anthropic


class InterviewAgent:
    """
    Autonomous AI agent that conducts intelligent interviews
    Maintains state, adapts questions, and evaluates responses
    """
    
    def __init__(self, session: InterviewSession):
        self.session = session
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"
        
        # Initialize agent state if not exists
        if not self.session.agent_state:
            self.session.agent_state = {
                'current_stage': 'greeting',
                'questions_asked': 0,
                'performance_level': 'medium',  # low, medium, high
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

RESPONSE FORMAT:
Respond with a JSON object:
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

Be conversational, professional, and adaptive. Your goal is to assess the candidate fairly while making them comfortable.
"""
    
    def process_message(self, candidate_message: str):
        """
        Process candidate's message and generate intelligent response
        This is the core agentic decision-making function
        """
        
        # Add candidate message to conversation history
        self.session.conversation_history.append({
            'role': 'user',
            'content': candidate_message,
            'timestamp': timezone.now().isoformat()
        })
        
        # Build conversation for Claude
        messages = self._build_conversation_context()
        
        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=self.get_system_prompt(),
                messages=messages
            )
            
            agent_response = response.content[0].text
            
            # Parse JSON response
            try:
                response_data = json.loads(agent_response)
            except json.JSONDecodeError:
                # Fallback if not valid JSON
                response_data = {
                    'message': agent_response,
                    'action': 'ask_question',
                    'stage': self.session.agent_state.get('current_stage', 'greeting')
                }
            
            # Store agent response
            self.session.conversation_history.append({
                'role': 'assistant',
                'content': response_data['message'],
                'metadata': response_data,
                'timestamp': timezone.now().isoformat()
            })
            
            # Update agent state based on response
            self._update_agent_state(response_data, candidate_message)
            
            self.session.save()
            
            return response_data
            
        except Exception as e:
            print(f"Agent error: {e}")
            return {
                'message': "I apologize, but I'm having technical difficulties. Let's continue with the interview.",
                'action': 'ask_question',
                'stage': self.session.agent_state.get('current_stage', 'greeting')
            }
    
    def _build_conversation_context(self):
        """Build message history for Claude API"""
        messages = []
        
        for msg in self.session.conversation_history:
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
        """Generate comprehensive evaluation report at the end"""
        
        questions = Question.objects.filter(session=self.session)
        avg_score = sum(q.score for q in questions if q.score) / max(len(questions), 1)
        
        evaluation_prompt = f"""
Based on the complete interview with {self.session.candidate_name}, generate a comprehensive evaluation report.

INTERVIEW SUMMARY:
- Total Questions: {questions.count()}
- Average Score: {avg_score:.2f}/10
- Cheating Violations: {self.session.cheating_score}
- Duration: {(self.session.completed_at - self.session.started_at).seconds // 60} minutes

Please provide:
1. Overall Performance Assessment (2-3 sentences)
2. Technical Skills Rating (1-10)
3. Communication Skills Rating (1-10)
4. Strengths (bullet points)
5. Areas for Improvement (bullet points)
6. Hiring Recommendation (Strong Yes / Yes / Maybe / No)
7. Additional Comments

Format as a professional evaluation report.
"""
        
        messages = [{
            'role': 'user',
            'content': evaluation_prompt
        }]
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system="You are an expert interviewer providing a final evaluation report. Be honest, constructive, and professional.",
                messages=messages
            )
            
            evaluation_text = response.content[0].text
            
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