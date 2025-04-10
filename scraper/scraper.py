import requests
from bs4 import BeautifulSoup
import time
import random
from pymongo import MongoClient
from urllib.parse import urlparse
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scraper.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GoogleScraper:
    def __init__(self, api_key=config.API_KEY, cx=config.CX, 
                 delay=config.DEFAULT_DELAY, 
                 user_agent=config.DEFAULT_USER_AGENT):
        self.api_key = api_key
        self.cx = cx
        self.delay = delay
        self.headers = {'User-Agent': user_agent}
        self.excluded_domains = config.EXCLUDED_DOMAINS
        
        # Connect to MongoDB
        self.client = MongoClient(config.MONGO_URI)
        self.db = self.client[config.DATABASE_NAME]
        self.collection = self.db['raw_reviews']
        
        logger.info("GoogleScraper initialized")
    
    # Rest of the code remains the same
    def is_excluded_domain(self, url):
        """Check if the URL belongs to an excluded domain."""
        domain = urlparse(url).netloc
        return any(excluded in domain for excluded in self.excluded_domains)
    
    def search(self, query, num_results=config.DEFAULT_RESULTS_LIMIT):
        """Perform a Google search and return the results."""
        logger.info(f"Searching for: {query}")
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.api_key,
            'cx': self.cx,
            'q': query,
            'num': 10  # Request more to account for excluded domains
        }
        
        results = []
        start_index = 1
        
        while len(results) < num_results:
            params['start'] = start_index
            
            try:
                response = requests.get(url, params=params)
                data = response.json()
                
                if 'items' not in data:
                    logger.warning("No search results found or API limit reached")
                    break
                
                # Filter out excluded domains
                filtered_items = [item for item in data['items'] 
                                 if not self.is_excluded_domain(item.get('link', ''))]
                
                results.extend(filtered_items)
                
                if len(results) >= num_results or len(data['items']) < 10:
                    break
                
                start_index += 10
                time.sleep(self.delay)  # Respect rate limits
                
            except Exception as e:
                logger.error(f"Error during Google search: {e}")
                break
        
        logger.info(f"Found {len(results)} valid results after filtering excluded domains")
        return results[:num_results]
    
    def scrape_website(self, url):
        """Scrape content from a website."""
        logger.info(f"Scraping website: {url}")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract basic information
            title = soup.title.string if soup.title else "No title"
            
            # Extract all paragraphs
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
            
            # Extract all headings
            headings = []
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                headings.extend([h.get_text(strip=True) for h in soup.find_all(tag) if h.get_text(strip=True)])
            
            # Get domain name
            domain = urlparse(url).netloc
            
            return {
                'url': url,
                'domain': domain,
                'title': title,
                'headings': headings,
                'paragraphs': paragraphs,
                'html': response.text,
                'scraped_at': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    def run(self, query, num_results=config.DEFAULT_RESULTS_LIMIT):
        """Run the complete scraping process."""
        logger.info(f"Starting scraping process for query: {query}")
        
        # Get search results
        search_results = self.search(query, num_results)
        
        if not search_results:
            logger.warning("No search results to scrape")
            return []
        
        scraped_data = []
        
        # Scrape each result
        for result in search_results:
            url = result.get('link')
            
            if not url:
                continue
                
            # Add a random delay between requests
            time.sleep(self.delay + random.uniform(1, 2))
            
            data = self.scrape_website(url)
            
            if data:
                # Add search metadata
                data['search_query'] = query
                data['search_title'] = result.get('title', '')
                data['search_snippet'] = result.get('snippet', '')
                
                # Save to MongoDB
                self.collection.insert_one(data)
                
                scraped_data.append(data)
                logger.info(f"Saved data from {url}")
        
        logger.info(f"Completed scraping {len(scraped_data)} websites for query: {query}")
        return scraped_data