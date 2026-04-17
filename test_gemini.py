from dotenv import load_dotenv
import os

from langchain_google_genai import ChatGoogleGenerativeAI

# Load env
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini via LangChain
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",   # recommended stable model
    google_api_key=GEMINI_API_KEY,
    temperature=0.7
)

# Simple prompt
response = llm.invoke("Explain what is crop disease in simple terms")

print(response.content)