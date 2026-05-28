"""
Free Web Search module for Legal Knowledge Assistant.
Leverages DuckDuckGo's static HTML endpoint to retrieve real-time legal updates,
cases, and news without requiring any API keys or incurring costs.
"""

from __future__ import annotations

import logging
import urllib.parse
from typing import Dict, List
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def search_duckduckgo_free(query: str, limit: int = 5) -> List[Dict[str, str]]:
    """
    Query DuckDuckGo's static HTML search interface for free.
    
    Args:
        query: The search query string.
        limit: Max number of results to return.
        
    Returns:
        List of dicts, each with keys: 'title', 'url', 'snippet'
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    try:
        # Use a reasonable timeout to prevent blocking application response
        with httpx.Client(headers=headers, timeout=2.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning("DuckDuckGo static search failed with status: %d", resp.status_code)
                return []
            
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            
            result_elements = soup.find_all("div", class_="result")
            for elem in result_elements[:limit]:
                title_elem = elem.find("a", class_="result__a")
                snippet_elem = elem.find("a", class_="result__snippet")
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    raw_url = title_elem.get("href", "")
                    
                    parsed_url = raw_url
                    if "uddg=" in raw_url:
                        try:
                            qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                            if "uddg" in qs:
                                parsed_url = qs["uddg"][0]
                        except Exception:
                            pass
                    
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    results.append({
                        "title": title,
                        "url": parsed_url,
                        "snippet": snippet
                    })
            return results
    except Exception as e:
        logger.error("Error during DuckDuckGo search: %s", e)
        return []
