# FitBuddy - AI Fitness Plan Generator using Gemini Models

FitBuddy is a web-based application that uses AI to generate personalized workout plans and nutrition tips.

Built with FastAPI and Google's Gemini AI models.

### Features
- Generates 7-day personalized workout plan
- Nutrition / Recovery tips based on goal
- Feedback loop to update plan
- Admin dashboard to view all users

### Tech Stack
- FastAPI, SQLAlchemy, SQLite
- Gemini 1.5 Pro & Gemini Flash
- HTML, CSS, Jinja2

### How to Run
1. pip install -r requirements.txt
2. Create .env file -> GEMINI_API_KEY=your_api_key_here
3. uvicorn main:app --reload
4. Open http://127.0.0.1:8000

Project by kowsalyaperiyannan68-eng
