import streamlit as st
import os
import json
import datetime
import requests
from dotenv import load_dotenv
from openai import OpenAI
import wikipedia
import re
from bs4 import BeautifulSoup

# Import your StudyBuddyDB class and tools
from study_buddy_agent import StudyBuddyDB, available_tools

# Load environment variables
load_dotenv()

# Initialize the database
db = StudyBuddyDB()

# System prompt (updated to provide more detailed, comprehensive responses)
system_prompt = """
You are Study Buddy AI, a helpful AI assistant specialized in helping students learn effectively.
You work on start, plan, action, observe mode.

For the given user query and available tools, plan the step by step execution.
Based on the planning, select the relevant tool from the available tools.
And based on the tool selection you perform an action to call the tool.
Wait for the observation and based on the observation from the tool call, resolve the user query.

When interacting with users:
1. Maintain a friendly, encouraging tone with vibrant personality
2. Focus on making learning personal and exciting
3. Provide DETAILED and COMPREHENSIVE explanations - never be brief unless specifically asked
4. Include examples, analogies, and multiple perspectives when explaining concepts
5. Break down complex topics into digestible parts with thorough explanations
6. When teaching a topic, cover it in depth with proper structure (introduction, main concepts, examples, applications)

Rules:
1. Follow the strict json output as per output schema 
2. Always perform one step at a time and wait for next input
3. Carefully analyze the user query and determine which educational goal they're trying to achieve
4. Be encouraging and motivational in your final responses
5. Suggest next steps for the student based on their progress
6. Provide thorough, comprehensive answers - aim to teach the topic completely

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
- search_wikipedia: Searches Wikipedia for up-to-date information on a topic. Input format: "Albert Einstein"
- search_web: Searches the web for recent information on a topic. Input format: "latest developments in quantum computing"
- fetch_academic_resources: Fetches academic resources and papers on a subject. Input format: "deep learning"
"""

# New tools for accessing live information
def search_wikipedia(query, username="default_user"):
    """
    Searches Wikipedia for information on a specific topic.
    Input format: "Albert Einstein"
    """
    try:
        # Search Wikipedia
        search_results = wikipedia.search(query, results=3)
        
        if not search_results:
            return f"No Wikipedia results found for '{query}'."
        
        # Get the page for the first result
        try:
            page = wikipedia.page(search_results[0], auto_suggest=False)
        except wikipedia.DisambiguationError as e:
            # If disambiguation page, take the first option
            page = wikipedia.page(e.options[0], auto_suggest=False)
        
        # Get summary and sections
        summary = page.summary
        content = f"# {page.title}\n\n{summary}\n\n"
        
        # Add a few sections if available
        if len(page.sections) > 0:
            for section in page.sections[:3]:  # Limit to first 3 sections
                try:
                    section_content = page.section(section)
                    if section_content and len(section_content) > 10:  # Only add non-empty sections
                        content += f"## {section}\n\n{section_content}\n\n"
                except:
                    pass
        
        # Add reference
        content += f"\nSource: Wikipedia, Retrieved on {datetime.datetime.now().strftime('%Y-%m-%d')}"
        content += f"\nURL: {page.url}"
        
        return content
        
    except Exception as e:
        return f"Error searching Wikipedia: {str(e)}"

def search_web(query, username="default_user"):
    """
    Searches the web for recent information on a topic.
    Input format: "latest developments in quantum computing"
    """
    try:
        # Use a search API (simplified for example)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Try to get some educational content from Khan Academy
        url = f"https://www.khanacademy.org/search?page_search_query={query.replace(' ', '+')}"
        response = requests.get(url, headers=headers)
        
        content = f"# Web search results for: {query}\n\n"
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find search results
            results = soup.find_all('a', class_=re.compile('result'))
            
            if results:
                content += "## Khan Academy Resources:\n\n"
                for idx, result in enumerate(results[:5]):  # Limit to 5 results
                    title = result.get_text(strip=True)
                    link = "https://www.khanacademy.org" + result['href'] if result.has_attr('href') else ""
                    if title and link:
                        content += f"{idx+1}. [{title}]({link})\n"
            
        # Also try to find resources from Coursera
        url = f"https://www.coursera.org/search?query={query.replace(' ', '%20')}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find course cards
            results = soup.find_all('div', class_=re.compile('card'))
            
            if results:
                content += "\n## Coursera Courses:\n\n"
                for idx, result in enumerate(results[:5]):  # Limit to 5 results
                    title_elem = result.find('h2') or result.find('h3')
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    link_elem = result.find('a')
                    link = "https://www.coursera.org" + link_elem['href'] if link_elem and link_elem.has_attr('href') else ""
                    
                    if title and link:
                        content += f"{idx+1}. [{title}]({link})\n"
        
        content += f"\nSearch performed on: {datetime.datetime.now().strftime('%Y-%m-%d')}"
        return content
        
    except Exception as e:
        return f"Error searching the web: {str(e)}"

def fetch_academic_resources(subject, username="default_user"):
    """
    Fetches academic resources and papers on a subject.
    Input format: "deep learning"
    """
    try:
        content = f"# Academic Resources for: {subject}\n\n"
        
        # Try to get resources from arXiv
        url = f"https://arxiv.org/search/?query={subject.replace(' ', '+')}&searchtype=all"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find paper entries
            entries = soup.find_all('li', class_='arxiv-result')
            
            if entries:
                content += "## Recent arXiv Papers:\n\n"
                for idx, entry in enumerate(entries[:5]):  # Limit to 5 papers
                    title_elem = entry.find('p', class_='title')
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    authors_elem = entry.find('p', class_='authors')
                    authors = authors_elem.get_text(strip=True) if authors_elem else ""
                    
                    abstract_elem = entry.find('span', class_='abstract-full')
                    abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
                    
                    link_elem = entry.find('a', class_='abstract-full')
                    link = "https://arxiv.org" + link_elem['href'] if link_elem and link_elem.has_attr('href') else ""
                    
                    if title:
                        content += f"### {idx+1}. {title}\n"
                        if authors:
                            content += f"**Authors:** {authors}\n\n"
                        if abstract:
                            content += f"**Abstract:** {abstract[:300]}...\n\n"
                        if link:
                            content += f"[Read more]({link})\n\n"
        
        # Add MIT OpenCourseWare
        url = f"https://ocw.mit.edu/search/?q={subject.replace(' ', '+')}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find course entries
            entries = soup.find_all('div', class_=re.compile('course-card'))
            
            if entries:
                content += "## MIT OpenCourseWare:\n\n"
                for idx, entry in enumerate(entries[:5]):  # Limit to 5 courses
                    title_elem = entry.find('h2') or entry.find('h3')
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    link_elem = entry.find('a')
                    link = "https://ocw.mit.edu" + link_elem['href'] if link_elem and link_elem.has_attr('href') else ""
                    
                    if title and link:
                        content += f"{idx+1}. [{title}]({link})\n"
        
        content += f"\nResources retrieved on: {datetime.datetime.now().strftime('%Y-%m-%d')}"
        return content
        
    except Exception as e:
        return f"Error fetching academic resources: {str(e)}"

# Add new tools to available_tools dictionary
available_tools.update({
    "search_wikipedia": {
        "fn": search_wikipedia,
        "description": "Searches Wikipedia for information on a specific topic. Input format: 'Albert Einstein'"
    },
    "search_web": {
        "fn": search_web,
        "description": "Searches the web for recent information on a topic. Input format: 'latest developments in quantum computing'"
    },
    "fetch_academic_resources": {
        "fn": fetch_academic_resources,
        "description": "Fetches academic resources and papers on a subject. Input format: 'deep learning'"
    }
})

def run_conversation(query, username, api_key, base_url):
    """Run the conversation with the LLM and execute tools"""
    
    # Initialize client with user's API key
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
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
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "show_steps" not in st.session_state:
    st.session_state.show_steps = False

# API key and username setup
if not st.session_state.username or not st.session_state.api_key:
    with st.form("setup_form"):
        username = st.text_input("What's your name?", key="username_input")
        api_key = st.text_input("Your Groq API Key:", type="password", key="api_key_input", 
                               help="Get your API key from https://console.groq.com")
        base_url = st.selectbox("API Provider:", 
                              options=["https://api.groq.com/openai/v1"], 
                              index=0)
        
        submit_button = st.form_submit_button("Start Learning!")
        
        if submit_button:
            if not username:
                st.error("Please enter your name.")
            elif not api_key:
                st.error("Please enter your API key.")
            else:
                st.session_state.username = username
                st.session_state.api_key = api_key
                st.session_state.base_url = base_url
                st.session_state.conversation_history.append(f"🤖 Welcome, {username}! What would you like to study?")
                st.rerun()  # Updated from experimental_rerun()

# Main conversation area
if st.session_state.username and st.session_state.api_key:
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
            conversation_steps, final_output = run_conversation(
                query, 
                st.session_state.username, 
                st.session_state.api_key,
                st.session_state.base_url
            )
            
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
            st.rerun()  # Updated from experimental_rerun()
    
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
            st.rerun()  # Updated from experimental_rerun()
        
        if st.button("Check Progress"):
            st.session_state.conversation_history.append("👤 How is my progress?")
            st.rerun()  # Updated from experimental_rerun()
        
        if st.button("Generate Quiz"):
            if plan and plan['study_plan']:
                # Get the first incomplete topic
                for topic in plan['study_plan']:
                    if not topic['completed']:
                        st.session_state.conversation_history.append(f"👤 Generate a quiz on {topic['topic']}")
                        st.rerun()  # Updated from experimental_rerun()
                        break
            else:
                st.warning("Create a study plan first to generate quizzes")
        
        st.subheader("Research Tools")
        research_topic = st.text_input("Research Topic:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Search Wikipedia"):
                if research_topic:
                    st.session_state.conversation_history.append(f"👤 Search Wikipedia for: {research_topic}")
                    st.rerun()  # Updated from experimental_rerun()
                else:
                    st.warning("Please enter a topic")
        with col2:
            if st.button("Find Resources"):
                if research_topic:
                    st.session_state.conversation_history.append(f"👤 Find academic resources on: {research_topic}")
                    st.rerun()  # Updated from experimental_rerun()
                else:
                    st.warning("Please enter a topic")
        
        if st.button("Clear Conversation"):
            st.session_state.conversation_history = [f"🤖 Welcome back, {st.session_state.username}! What would you like to study?"]
            st.rerun()  # Updated from experimental_rerun()
        
        # API key management
        st.subheader("Settings")
        with st.expander("API Settings"):
            new_api_key = st.text_input("Update API Key:", type="password")
            if st.button("Update"):
                if new_api_key:
                    st.session_state.api_key = new_api_key
                    st.success("API key updated!")
                    st.rerun()  # Updated from experimental_rerun()