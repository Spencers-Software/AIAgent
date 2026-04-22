import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', '')
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'issues.db')