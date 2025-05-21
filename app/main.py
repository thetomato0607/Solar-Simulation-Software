import os
import openai
from dotenv import load_dotenv

# ✅ Load .env from parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# ✅ Debug print
print("KEY LOADED:", os.getenv("OPENAI_API_KEY"))

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
