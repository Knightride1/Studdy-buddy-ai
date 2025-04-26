# Study Buddy AI 📚

A personalized AI learning assistant that helps students create study plans, take quizzes, track progress, and answer subject-specific questions.

## Features ✨

- 🗓️ **Personalized Study Plans**: Create customized learning schedules based on your subjects and timeline
- ❓ **Subject-Specific Q&A**: Get instant answers to your academic questions
- 📝 **Quiz Generation**: Test your knowledge with auto-generated quizzes on any topic
- 📊 **Progress Tracking**: Monitor your learning journey with detailed progress reports
- 📚 **Learning Materials**: Access comprehensive study materials for any topic

## Tech Stack 🛠️

- Python 3.8+
- SQLite database for storing user data, study plans, and quizzes
- Groq LLM API for AI assistant capabilities
- Terminal-based interface (with optional web deployment)

## Installation 💻

### Prerequisites

- Python 3.8+
- Groq API key (sign up at [groq.com](https://console.groq.com))

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/study-buddy-ai.git
   cd study-buddy-ai
   ```

2. **Set up a virtual environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root directory:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

5. **Initialize the database**
   
   The database will be automatically created when you run the application for the first time.

## Usage 🚀

Run the application with:
```bash
python study_buddy.py
```

Follow the prompts to:
1. Enter your username
2. Specify what you want to study
3. Start learning with personalized assistance!

## Example Commands 💬

- **Create a study plan**: "I want to learn Math and master Algebra in 2 weeks"
- **Ask a question**: "Can you explain how to solve 2x + 3 = 7?"
- **Generate a quiz**: "Create a quiz on Linear Equations"
- **Check progress**: "How am I doing with my studies?"
- **Get learning materials**: "Show me study material for Quadratic Equations"

## Project Structure 📁

```
study-buddy-ai/
├── .env                      # Environment variables
├── requirements.txt          # Project dependencies
├── study_buddy.py            # Main application code
├── study_buddy.db            # SQLite database (auto-generated)
└── README.md                 # Project documentation
```

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.