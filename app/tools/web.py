# app/tools/web.py
from langchain_core.tools import tool
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup
from app.config import WEB_SEARCH_MAX_RESULTS, WEB_PAGE_MAX_CHARS
from app.logger import get_logger

logger = get_logger("web_tools")

@tool
def web_search(query: str):
    """
    Search the internet using DuckDuckGo.
    Use this to find documentation, error solutions, or libraries.
    """
    try:
        # max_results=3 pour économiser le contexte du petit modèle
        results = DDGS().text(query, max_results=WEB_SEARCH_MAX_RESULTS)
        if not results:
            return "No results found."
        
        formatted = []
        for res in results:
            formatted.append(f"Titre: {res['title']}\nLien: {res['href']}\nRésumé: {res['body']}")
            
        return "\n---\n".join(formatted)
    except Exception as e:
        return f"Search error: {str(e)}"

@tool
def fetch_web_page(url: str):
    """
    Fetch the content of a specific URL.
    Use this when web_search snippets are not detailed enough.
    """
    logger.info(f"🕷️ SCRAPING: {url}")
    try:
        # On se fait passer pour un vrai navigateur (User-Agent) pour ne pas être bloqué
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        # response.raise_for_status() # On évite ça pour gérer l'erreur manuellement ci-dessous
        
        if response.status_code != 200:
               return f"HTTP error {response.status_code} accessing {url}"

        # Nettoyage du HTML avec BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # On supprime les scripts et les styles inutiles
        for script in soup(["script", "style", "nav", "footer", "svg"]):
            script.decompose()
            
        # On récupère le texte
        text = soup.get_text(separator='\n')
        
        # On nettoie les espaces vides
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # On limite la taille pour ne pas tuer le LLM (5000 caractères max)
        if len(clean_text) > WEB_PAGE_MAX_CHARS:
            return clean_text[:WEB_PAGE_MAX_CHARS] + "\n... [Contenu tronqué]"
        
        return clean_text

    except Exception as e:
        return f"Error fetching page: {e}"
    
@tool
def smart_web_fetch(query: str):
    """
    Search DuckDuckGo + fetch best result in one shot.
    Use this for research tasks requiring page content.
    """
    try:
        # 1. Search
        results = DDGS().text(query, max_results=5)
        if not results:
            return "No results found."
        
        # 2. Pick best URL (priorité docs officielles)
        best = results[0]
        priority_domains = ['docs.', 'github.com', 'python.org', 'stackoverflow.com']
        for r in results:
            if any(domain in r['href'] for domain in priority_domains):
                best = r
                break
        
        url = best['href']
        logger.info(f"🕷️ SMART FETCH: {url}")
        
        # 3. Fetch
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return f"Error HTTP {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
        
        text = soup.get_text(separator='\n')
        lines = (line.strip() for line in text.splitlines())
        clean = '\n'.join(line for line in lines if line)
        
        if len(clean) > WEB_PAGE_MAX_CHARS:
            return clean[:WEB_PAGE_MAX_CHARS] + "\n...[truncated]"
        
        return clean
        
    except Exception as e:
        return f"Error: {e}"