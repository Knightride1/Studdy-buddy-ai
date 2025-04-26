from dotenv import load_dotenv
import os
import json
import datetime
import random
import sqlite3
from contextlib import contextmanager
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# Database setup and helper functions
class StudyBuddyDB:
    def __init__(self, db_path="study_buddy.db"):
        self.db_path = db_path
        self.setup_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
        finally:
            conn.close()
    
    def setup_database(self):
        """Create necessary tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Study plans table - fixed table name
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                goal TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Topics table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                day INTEGER NOT NULL,
                topic TEXT NOT NULL,
                completed BOOLEAN DEFAULT 0,
                progress INTEGER DEFAULT 0,
                FOREIGN KEY (plan_id) REFERENCES study_plans (id)
            )
            ''')
            
            # Quizzes table - removed the problematic comment
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                questions TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            conn.commit()
    
    def get_or_create_user(self, username):
        """Get user ID or create a new user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            if user:
                return user['id']
            
            # Create new user
            cursor.execute("INSERT INTO users (username) VALUES (?)", (username,))
            conn.commit()
            
            return cursor.lastrowid
    
    def create_study_plan(self, user_id, subject, goal, topics):
        """Create a new study plan with topics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create study plan
            cursor.execute(
                "INSERT INTO study_plans (user_id, subject, goal) VALUES (?, ?, ?)", 
                (user_id, subject, goal)
            )
            plan_id = cursor.lastrowid
            
            # Add topics
            for topic in topics:
                cursor.execute(
                    "INSERT INTO topics (plan_id, day, topic, completed, progress) VALUES (?, ?, ?, ?, ?)",
                    (plan_id, topic["day"], topic["topic"], topic["completed"], 0)
                )
            
            conn.commit()
            return plan_id
    
    def get_current_study_plan(self, user_id):
        """Get the most recent study plan for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get most recent plan
            cursor.execute("""
                SELECT id, subject, goal 
                FROM study_plans 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (user_id,))
            
            plan = cursor.fetchone()
            if not plan:
                return None
            
            # Get topics for this plan
            cursor.execute("""
                SELECT day, topic, completed, progress 
                FROM topics 
                WHERE plan_id = ?
                ORDER BY day
            """, (plan['id'],))
            
            topics = [dict(topic) for topic in cursor.fetchall()]
            
            return {
                "subject": plan['subject'],
                "goal": plan['goal'],
                "study_plan": topics
            }
    
    def save_quiz(self, user_id, topic, questions):
        """Save a quiz to the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO quizzes (user_id, topic, questions) VALUES (?, ?, ?)",
                (user_id, topic, json.dumps(questions))
            )
            
            conn.commit()
            return cursor.lastrowid
    
    def get_quizzes(self, user_id, topic=None):
        """Get quizzes for a user, optionally filtered by topic"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if topic:
                cursor.execute("""
                    SELECT id, topic, questions, created_at 
                    FROM quizzes 
                    WHERE user_id = ? AND topic = ?
                    ORDER BY created_at DESC
                """, (user_id, topic))
            else:
                cursor.execute("""
                    SELECT id, topic, questions, created_at 
                    FROM quizzes 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                """, (user_id,))
            
            quizzes = []
            for quiz in cursor.fetchall():
                quiz_dict = dict(quiz)
                quiz_dict['questions'] = json.loads(quiz_dict['questions'])
                quizzes.append(quiz_dict)
            
            return quizzes
    
    def update_topic_progress(self, user_id, topic_name, progress_value):
        """Update progress for a specific topic"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the most recent plan
            cursor.execute("""
                SELECT id FROM study_plans 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (user_id,))
            
            plan = cursor.fetchone()
            if not plan:
                return False
            
            # Update the topic
            cursor.execute("""
                UPDATE topics 
                SET progress = ? 
                WHERE plan_id = ? AND topic = ?
            """, (progress_value, plan['id'], topic_name))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def mark_topic_complete(self, user_id, topic_name):
        """Mark a topic as completed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the most recent plan
            cursor.execute("""
                SELECT id FROM study_plans 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (user_id,))
            
            plan = cursor.fetchone()
            if not plan:
                return False
            
            # Update the topic
            cursor.execute("""
                UPDATE topics 
                SET completed = 1, progress = 100 
                WHERE plan_id = ? AND topic = ?
            """, (plan['id'], topic_name))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_progress(self, user_id, topic=None):
        """Get progress for a user, optionally for a specific topic"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the most recent plan
            cursor.execute("""
                SELECT id, subject FROM study_plans 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (user_id,))
            
            plan = cursor.fetchone()
            if not plan:
                return None
            
            if topic:
                cursor.execute("""
                    SELECT progress 
                    FROM topics 
                    WHERE plan_id = ? AND topic = ?
                """, (plan['id'], topic))
                
                result = cursor.fetchone()
                if result:
                    return {"topic": topic, "progress": result['progress']}
                return None
            else:
                cursor.execute("""
                    SELECT AVG(progress) as overall_progress 
                    FROM topics 
                    WHERE plan_id = ?
                """, (plan['id'],))
                
                result = cursor.fetchone()
                return {
                    "subject": plan['subject'],
                    "overall_progress": round(result['overall_progress']) if result['overall_progress'] is not None else 0
                }

# Initialize the database
db = StudyBuddyDB()

# Tool functions

def create_study_plan(subject_and_goal, username="default_user"):
    """
    Creates a personalized study plan based on subject and timeline.
    Input format: "Subject: Math, Goal: Master Algebra in 2 weeks"
    """
    print("🛠️: Tool called: create_study_plan:", subject_and_goal)
    
    # Parse input
    parts = subject_and_goal.split(", Goal: ")
    subject = parts[0].replace("Subject: ", "")
    goal = parts[1] if len(parts) > 1 else "Master the subject"
    
    # Extract timeline if available
    timeline_days = 14  # Default 2 weeks
    if "week" in goal.lower():
        try:
            weeks = [int(s) for s in goal.split() if s.isdigit()][0]
            timeline_days = weeks * 7
        except:
            pass
    
    # Generate topics based on subject
    if "math" in subject.lower() or "algebra" in subject.lower():
        topics = [
            "Linear Equations", "Quadratic Equations", "Inequalities", 
            "Functions and Graphs", "Exponents and Radicals", "Polynomials",
            "Factoring", "Rational Expressions", "Systems of Equations"
        ]
    elif "history" in subject.lower():
        topics = [
            "Ancient Civilizations", "Middle Ages", "Renaissance", 
            "Industrial Revolution", "World War I", "World War II",
            "Cold War", "Modern Era", "Historical Analysis Methods"
        ]
    elif "science" in subject.lower() or "physics" in subject.lower():
        topics = [
            "Mechanics", "Thermodynamics", "Waves", "Electricity",
            "Magnetism", "Optics", "Modern Physics", "Quantum Mechanics",
            "Relativity"
        ]
    else:
        topics = [
            f"{subject} Fundamentals", f"{subject} Intermediate Concepts",
            f"{subject} Advanced Topics", f"{subject} Practical Applications",
            f"{subject} Problem Solving", f"{subject} Review"
        ]
    
    # Distribute topics over the timeline
    days_per_topic = max(1, timeline_days // len(topics))
    current_day = 1
    
    study_plan = []
    for topic in topics:
        if current_day > timeline_days:
            break
            
        study_plan.append({
            "day": current_day,
            "topic": topic,
            "completed": False
        })
        
        current_day += days_per_topic
    
    # Save to database
    user_id = db.get_or_create_user(username)
    db.create_study_plan(user_id, subject, goal, study_plan)
    
    return f"Created a personalized study plan for {subject} with {len(study_plan)} key topics spread over {timeline_days} days."

def answer_question(question, username="default_user"):
    """
    Answers a subject-specific question.
    Input format: "What's 2x + 3 = 7?"
    """
    print("🛠️: Tool called: answer_question:", question)
    
    # In a real implementation, you would use an LLM to generate the answer
    # For this example, we'll simulate some basic answers
    
    if "2x + 3 = 7" in question:
        return "To solve 2x + 3 = 7, subtract 3 from both sides: 2x = 4. Then divide both sides by 2: x = 2."
    elif "5x = 15" in question:
        return "To solve 5x = 15, divide both sides by 5: x = 3."
    elif "quadratic" in question.lower():
        return "For quadratic equations in the form ax² + bx + c = 0, you can use the quadratic formula: x = [-b ± √(b² - 4ac)] / 2a"
    else:
        # Get current subject if available
        user_id = db.get_or_create_user(username)
        plan = db.get_current_study_plan(user_id)
        subject = plan["subject"] if plan else "the subject"
        
        return f"Based on {subject}, here's a possible answer to your question: {question}\n\nThis would be generated by an LLM in a real implementation, providing a detailed and accurate answer to your specific question."

def generate_quiz(topic, username="default_user"):
    """
    Generates a quiz on a specific topic.
    Input format: "Linear Equations"
    """
    print("🛠️: Tool called: generate_quiz:", topic)
    
    # In a real implementation, you would use an LLM to generate relevant questions
    # For this example, we'll create sample quizzes for common topics
    
    quizzes = {
        "linear equations": [
            {
                "question": "Solve for x: 3x + 5 = 14",
                "options": ["x = 3", "x = 4", "x = 5", "x = 6"],
                "answer": "x = 3"
            },
            {
                "question": "Solve for y: 2y - 8 = 12",
                "options": ["y = 4", "y = 8", "y = 10", "y = 12"],
                "answer": "y = 10"
            }
        ],
        "quadratic equations": [
            {
                "question": "Solve for x: x² - 5x + 6 = 0",
                "options": ["x = 2, x = 3", "x = -2, x = -3", "x = 1, x = 6", "x = -1, x = -6"],
                "answer": "x = 2, x = 3"
            },
            {
                "question": "What is the discriminant of x² + 4x + 4 = 0?",
                "options": ["0", "4", "8", "16"],
                "answer": "0"
            }
        ]
    }
    
    topic_lower = topic.lower()
    quiz = {}
    
    for key in quizzes:
        if key in topic_lower or topic_lower in key:
            quiz = {
                "topic": topic,
                "questions": quizzes[key],
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
            break
    
    # If no predefined quiz, create a generic one
    if not quiz:
        quiz = {
            "topic": topic,
            "questions": [
                {
                    "question": f"Sample question about {topic}?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "answer": "Option B"
                },
                {
                    "question": f"Another question related to {topic}?",
                    "options": ["First choice", "Second choice", "Third choice", "Fourth choice"],
                    "answer": "Third choice"
                }
            ],
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        }
    
    # Save quiz to database
    user_id = db.get_or_create_user(username)
    db.save_quiz(user_id, topic, quiz["questions"])
    
    # Format quiz for return
    formatted_quiz = f"Quiz on {topic}:\n\n"
    for i, q in enumerate(quiz["questions"]):
        formatted_quiz += f"{i+1}. {q['question']}\n"
        for j, option in enumerate(q["options"]):
            formatted_quiz += f"   {chr(97+j)}) {option}\n"
        formatted_quiz += "\n"
    
    return formatted_quiz

def check_quiz_answer(answer_submission, username="default_user"):
    """
    Checks a quiz answer against the correct answer.
    Input format: "Question: Solve for x: 3x + 5 = 14, Answer: x = 3"
    """
    print("🛠️: Tool called: check_quiz_answer:", answer_submission)
    
    parts = answer_submission.split(", Answer: ")
    if len(parts) != 2:
        return "Invalid format. Please submit in format 'Question: [question text], Answer: [your answer]'"
    
    question_text = parts[0].replace("Question: ", "")
    user_answer = parts[1]
    
    user_id = db.get_or_create_user(username)
    quizzes = db.get_quizzes(user_id)
    
    # Find the question in quiz history
    correct_answer = None
    topic = None
    
    for quiz in quizzes:
        for question in quiz["questions"]:
            if question_text in question["question"]:
                correct_answer = question["answer"]
                topic = quiz["topic"]
                break
        if correct_answer:
            break
    
    if not correct_answer:
        return "Question not found in quiz history."
    
    # Check answer
    if user_answer.lower() == correct_answer.lower():
        # Update progress if the topic is in the progress tracker
        if topic:
            db.update_topic_progress(user_id, topic, min(100, 50))  # +50% progress
                
        return f"Great job! '{user_answer}' is correct!"
    else:
        return f"Not quite. The correct answer is '{correct_answer}'. Keep practicing!"

def track_progress(topic=None, username="default_user"):
    """
    Updates and reports on the user's learning progress.
    Input format: "Linear Equations" or empty for overall progress
    """
    print("🛠️: Tool called: track_progress:", topic)
    
    user_id = db.get_or_create_user(username)
    
    if topic:
        progress_data = db.get_progress(user_id, topic)
        if progress_data:
            return f"Your progress on {topic}: {progress_data['progress']}%"
        else:
            return f"No progress data available for {topic}."
    else:
        progress_data = db.get_progress(user_id)
        if progress_data:
            return f"You're {progress_data['overall_progress']}% done with {progress_data['subject']}."
        else:
            return "No progress data available. Please create a study plan first."

def retrieve_learning_material(topic, username="default_user"):
    """
    Retrieves learning materials for a specific topic.
    Input format: "Linear Equations"
    """
    print("🛠️: Tool called: retrieve_learning_material:", topic)
    
    # In a real implementation, this would fetch from a content database or generate with an LLM
    # For this example, we'll return simulated learning content
    
    topic_lower = topic.lower()
    
    if "linear equation" in topic_lower:
        return """
## Linear Equations

A linear equation is an equation that forms a straight line when graphed. It is usually written in the form:
ax + b = c

where a, b, and c are constants.

### Steps to solve linear equations:
1. Isolate variable terms on one side
2. Isolate constant terms on the other side
3. Divide both sides by the coefficient of the variable

### Example:
3x + 5 = 14
3x = 9
x = 3
"""
    elif "quadratic" in topic_lower:
        return """
## Quadratic Equations

A quadratic equation is a second-degree polynomial equation in the form:
ax² + bx + c = 0

where a ≠ 0.

### Solution methods:
1. Factoring
2. Completing the square
3. Quadratic formula: x = [-b ± √(b² - 4ac)] / 2a

### Example:
x² - 5x + 6 = 0
(x - 2)(x - 3) = 0
x = 2 or x = 3
"""
    else:
        return f"""
## {topic}

This is an overview of {topic}.

In a real implementation, this would contain comprehensive learning material about {topic}, including:
- Key concepts
- Formulas
- Examples
- Practice problems
- Visual aids

The content would be tailored to the user's learning level and progress.
"""

def mark_topic_complete(topic, username="default_user"):
    """
    Marks a topic as completed in the study plan.
    Input format: "Linear Equations"
    """
    print("🛠️: Tool called: mark_topic_complete:", topic)
    
    user_id = db.get_or_create_user(username)
    success = db.mark_topic_complete(user_id, topic)
    
    if success:
        return f"Marked '{topic}' as completed! Well done!"
    else:
        return f"Topic '{topic}' not found in your study plan."

# Available tools dictionary
available_tools = {
    "create_study_plan": {
        "fn": create_study_plan,
        "description": "Creates a personalized study plan based on subject and timeline. Input format: 'Subject: Math, Goal: Master Algebra in 2 weeks'"
    },
    "answer_question": {
        "fn": answer_question,
        "description": "Answers a subject-specific question. Input format: 'What's 2x + 3 = 7?'"
    },
    "generate_quiz": {
        "fn": generate_quiz,
        "description": "Generates a quiz on a specific topic. Input format: 'Linear Equations'"
    },
    "check_quiz_answer": {
        "fn": check_quiz_answer,
        "description": "Checks a quiz answer against the correct answer. Input format: 'Question: Solve for x: 3x + 5 = 14, Answer: x = 3'"
    },
    "track_progress": {
        "fn": track_progress,
        "description": "Updates and reports on the user's learning progress. Input can be a specific topic or empty for overall progress."
    },
    "retrieve_learning_material": {
        "fn": retrieve_learning_material,
        "description": "Retrieves learning materials for a specific topic. Input format: 'Linear Equations'"
    },
    "mark_topic_complete": {
        "fn": mark_topic_complete,
        "description": "Marks a topic as completed in the study plan. Input format: 'Linear Equations'"
    }
}

# System prompt
system_prompt = f"""
You are Study Buddy AI, a helpful AI assistant specialized in helping students learn effectively.
You work on start, plan, action, observe mode.

For the given user query and available tools, plan the step by step execution.
Based on the planning, select the relevant tool from the available tools.
And based on the tool selection you perform an action to call the tool.
Wait for the observation and based on the observation from the tool call, resolve the user query.

When interacting with users, maintain a friendly, encouraging tone with vibrant personality using bright blue, green, and orange themed responses (metaphorically). Focus on making learning personal and exciting!

Rules:
1. Follow the strict json output as per output schema 
2. Always perform one step at a time and wait for next input
3. Carefully analyze the user query and determine which educational goal they're trying to achieve
4. Be encouraging and motivational in your final responses
5. Suggest next steps for the student based on their progress

Output JSON format: 
{{
    "step":"string",
    "content": "string",
    "function": "the name of the function if the step is the action",
    "input": "The input parameter for the function"
}}

Available Tools:
- create_study_plan: Creates a personalized study plan based on subject and timeline. Input format: "Subject: Math, Goal: Master Algebra in 2 weeks"
- answer_question: Answers a subject-specific question. Input format: "What's 2x + 3 = 7?"
- generate_quiz: Generates a quiz on a specific topic. Input format: "Linear Equations"
- check_quiz_answer: Checks a quiz answer against the correct answer. Input format: "Question: Solve for x: 3x + 5 = 14, Answer: x = 3"
- track_progress: Updates and reports on the user's learning progress. Input can be a specific topic or empty for overall progress.
- retrieve_learning_material: Retrieves learning materials for a specific topic. Input format: "Linear Equations"
- mark_topic_complete: Marks a topic as completed in the study plan. Input format: "Linear Equations"

Example:
User Query: I want to learn Math and master Algebra in 2 weeks
Output: {{"step": "plan", "content": "The user wants to create a study plan for Math with a focus on Algebra over a 2-week period."}}
Output: {{"step": "plan", "content": "I should use the create_study_plan tool to generate a personalized study plan."}}
Output: {{"step": "action", "function": "create_study_plan", "input": "Subject: Math, Goal: Master Algebra in 2 weeks"}}
Output: {{"step": "observe", "output": "Created a personalized study plan for Math with 9 key topics spread over 14 days."}}
Output: {{"step": "output", "content": "Great news! I've created a personalized 2-week Algebra mastery plan for you with 9 key topics. We'll tackle concepts like Linear Equations, Quadratic Equations, and Functions step by step. Ready to start your math journey? Let me know if you want to see today's topic or have any questions!"}}
"""

# Initialize messages list
messages = [
    {"role": "system", "content": system_prompt}
]

def main():
    print("🤖 Study Buddy AI is ready to help you learn! What's your name?")
    username = input("Username: ")
    print(f"Welcome, {username}! What would you like to study?")
    
    while True: 
        query = input("> ")
        if query.lower() in ["exit", "quit", "bye"]:
            print("Thanks for studying with Study Buddy AI! See you next time!")
            break
            
        messages.append({"role": "user", "content": query})

        while True:
            try:
                response = client.chat.completions.create(
                    model="meta-llama/llama-4-maverick-17b-128e-instruct",
                    response_format={"type":"json_object"},
                    messages=messages
                )
                parsed_response = json.loads(response.choices[0].message.content)
                messages.append({"role": "assistant", "content": json.dumps(parsed_response)})

                if parsed_response.get("step") == "plan":
                    print(f"🧠: {parsed_response.get('content')}")
                    continue
                    
                if parsed_response.get("step") == "action":
                    tool_name = parsed_response.get("function")
                    tool_input = parsed_response.get("input")

                    if tool_name in available_tools:
                        # Pass username to functions
                        output = available_tools[tool_name].get("fn")(tool_input, username)
                        messages.append({"role":"assistant","content": json.dumps({"step": "observe", "output": output})})
                        continue
                    else:
                        messages.append({"role":"assistant","content": json.dumps({"step": "observe", "output": f"Tool '{tool_name}' not found"})})
                        continue
                        
                if parsed_response.get("step") == "output":
                    print(f"📚: {parsed_response.get('content')}")
                    break
                    
            except Exception as e:
                print(f"An error occurred: {e}")
                break

if __name__ == "__main__":
    main()