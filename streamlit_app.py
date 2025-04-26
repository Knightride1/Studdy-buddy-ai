import streamlit as st
import os
import json
import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Import your StudyBuddyDB class and tools
from study_buddy_agent import StudyBuddyDB, available_tools

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# Initialize the database
db = StudyBuddyDB()

# System prompt (same as in the original file)
system_prompt = """
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
{
    "step":"string",
    "content": "string",
    "function": "the name of the function if the step is the action",
    "input": "The input parameter for the function"
}

Available Tools:
- create_study_plan: Creates a personalized study plan based on subject and timeline. Input format: "Subject: Math, Goal: Master Algebra in 2 weeks"
- answer_question: Answers a subject-specific question. Input format: "What's 2x + 3 = 7?"
- generate_quiz: Generates a quiz on a specific topic. Input format: "Linear Equations"
- check_quiz_answer: Checks a quiz answer against the correct answer. Input format: "Question: Solve for x: 3x + 5 = 14, Answer: x = 3"
- track_progress: Updates and reports on the user's learning progress. Input can be a specific topic or empty for overall progress.
- retrieve_learning_material: Retrieves learning materials for a specific topic. Input format: "Linear Equations"
- mark_topic_complete: Marks a topic as completed in the study plan. Input format: "Linear Equations"
"""

def run_conversation(query, username):
    """Run the conversation with the LLM and execute tools"""
    
    # Initialize messages list
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]
    
    conversation_steps = []
    final_output = None
    
    while True:
        try:
            # Get response from LLM
            response = client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                response_format={"type":"json_object"},
                messages=messages
            )
            
            parsed_response = json.loads(response.choices[0].message.content)
            messages.append({"role": "assistant", "content": json.dumps(parsed_response)})
            
            if parsed_response.get("step") == "plan":
                conversation_steps.append(("plan", parsed_response.get("content")))
                continue
                
            if parsed_response.get("step") == "action":
                tool_name = parsed_response.get("function")
                tool_input = parsed_response.get("input")
                
                conversation_steps.append(("action", f"Using {tool_name} with input: {tool_input}"))

                if tool_name in available_tools:
                    # Pass username to functions
                    output = available_tools[tool_name].get("fn")(tool_input, username)
                    messages.append({"role":"assistant","content": json.dumps({"step": "observe", "output": output})})
                    conversation_steps.append(("observe", output))
                    continue
                else:
                    messages.append({"role":"assistant","content": json.dumps({"step": "observe", "output": f"Tool '{tool_name}' not found"})})
                    conversation_steps.append(("observe", f"Tool '{tool_name}' not found"))
                    continue
                    
            if parsed_response.get("step") == "output":
                final_output = parsed_response.get("content")
                break
                
        except Exception as e:
            final_output = f"An error occurred: {e}"
            break
            
    return conversation_steps, final_output

# Streamlit app
st.set_page_config(
    page_title="Study Buddy AI",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Study Buddy AI")
st.subheader("Your Personal Learning Assistant")

# Initialize session state
if "username" not in st.session_state:
    st.session_state.username = ""
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "show_steps" not in st.session_state:
    st.session_state.show_steps = False

# Username input
if not st.session_state.username:
    with st.form("username_form"):
        username = st.text_input("What's your name?", key="username_input")
        submit_button = st.form_submit_button("Start Learning!")
        
        if submit_button and username:
            st.session_state.username = username
            st.session_state.conversation_history.append(f"🤖 Welcome, {username}! What would you like to study?")
            st.experimental_rerun()

# Main conversation area
if st.session_state.username:
    # Display conversation history
    for message in st.session_state.conversation_history:
        st.write(message)
    
    # Input for new query
    with st.form("query_form"):
        query = st.text_input("What would you like to learn about?", key="query_input")
        col1, col2, col3 = st.columns([1, 1, 5])
        with col1:
            submit_button = st.form_submit_button("Send")
        with col2:
            toggle_steps = st.form_submit_button("Toggle Steps")
            if toggle_steps:
                st.session_state.show_steps = not st.session_state.show_steps
        
        if submit_button and query:
            st.session_state.conversation_history.append(f"👤 {query}")
            
            # Process the query
            conversation_steps, final_output = run_conversation(query, st.session_state.username)
            
            # Display step-by-step execution if toggled on
            if st.session_state.show_steps:
                step_expander = st.expander("View execution steps", expanded=True)
                with step_expander:
                    for step_type, step_content in conversation_steps:
                        if step_type == "plan":
                            st.info(f"🧠 Planning: {step_content}")
                        elif step_type == "action":
                            st.warning(f"⚙️ Action: {step_content}")
                        elif step_type == "observe":
                            st.success(f"👁️ Observation: {step_content}")
            
            # Display final output
            st.session_state.conversation_history.append(f"📚 {final_output}")
            
            # Clear the input
            st.experimental_rerun()
    
    # Sidebar with additional options
    with st.sidebar:
        st.header(f"Hello, {st.session_state.username}! 👋")
        
        # Display current study plan if available
        user_id = db.get_or_create_user(st.session_state.username)
        plan = db.get_current_study_plan(user_id)
        
        if plan:
            st.subheader("Your Current Study Plan")
            st.write(f"Subject: {plan['subject']}")
            st.write(f"Goal: {plan['goal']}")
            
            progress_data = db.get_progress(user_id)
            if progress_data:
                st.progress(progress_data['overall_progress'] / 100)
                st.write(f"Overall Progress: {progress_data['overall_progress']}%")
            
            st.subheader("Topics")
            for topic in plan['study_plan']:
                if topic['completed']:
                    st.success(f"✓ Day {topic['day']}: {topic['topic']} ({topic['progress']}%)")
                else:
                    st.write(f"□ Day {topic['day']}: {topic['topic']} ({topic['progress']}%)")
        
        # Quick actions
        st.subheader("Quick Actions")
        if st.button("Create Study Plan"):
            st.session_state.conversation_history.append("👤 I want to create a new study plan")
            st.experimental_rerun()
        
        if st.button("Check Progress"):
            st.session_state.conversation_history.append("👤 How is my progress?")
            st.experimental_rerun()
        
        if st.button("Generate Quiz"):
            if plan and plan['study_plan']:
                # Get the first incomplete topic
                for topic in plan['study_plan']:
                    if not topic['completed']:
                        st.session_state.conversation_history.append(f"👤 Generate a quiz on {topic['topic']}")
                        st.experimental_rerun()
                        break
            else:
                st.warning("Create a study plan first to generate quizzes")
        
        if st.button("Clear Conversation"):
            st.session_state.conversation_history = [f"🤖 Welcome back, {st.session_state.username}! What would you like to study?"]
            st.experimental_rerun