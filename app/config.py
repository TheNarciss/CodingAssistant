from pathlib import Path
import time
import os 
from dotenv import load_dotenv

load_dotenv()


# Paths
BASE_DIR = Path(__file__).resolve().parent
SANDBOX_NAME = "PlaygroundForCodingAssistant"  
SANDBOX_PATH = BASE_DIR / SANDBOX_NAME

# LLM Settings
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "llama3.2:3b"
MODEL_TEMPERATURE = 0.0
MODEL_KEEP_ALIVE = "5m"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "OPENROUTER") 
OPEN_API_KEY = os.getenv("OPEN_API_KEY", "")
OPEN_MODEL = os.getenv("OPEN_MODEL", "gemini-2.0-flash")

# Agent Limits
MAX_RETRIES = 3
MAX_CONTEXT_MESSAGES = 15
MAX_PLAN_STEPS = 5

# Web Search
WEB_SEARCH_MAX_RESULTS = 5
WEB_PAGE_MAX_CHARS = 5000

# Tool Limits
FILE_CONTENT_MAX_CHARS = 10000
MIN_FILE_CONTENT_LENGTH = 10
MAX_ITERATIONS = 30
class PlanCache:
    def __init__(self, ttl=300, maxsize=50):
        self.cache = {}
        self.ttl = ttl
        self.maxsize = maxsize
    
    def get(self, query: str):
        if query in self.cache:
            plan, timestamp = self.cache[query]
            if time.time() - timestamp < self.ttl:
                return plan
            del self.cache[query]
        return None
    
    def set(self, query: str, plan: dict):
        if len(self.cache) >= self.maxsize:
            oldest_key = min(self.cache, key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        self.cache[query] = (plan, time.time())

plan_cache = PlanCache()