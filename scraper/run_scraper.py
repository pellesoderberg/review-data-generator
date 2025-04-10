import argparse
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scraper import GoogleScraper

def main():
    parser = argparse.ArgumentParser(description='Google Search and Website Scraper')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--results', type=int, default=config.DEFAULT_RESULTS_LIMIT, 
                        help='Number of search results to process')
    parser.add_argument('--delay', type=float, default=config.DEFAULT_DELAY,
                        help='Delay between requests in seconds')
    
    args = parser.parse_args()
    
    scraper = GoogleScraper(delay=args.delay)
    scraper.run(args.query, args.results)

if __name__ == "__main__":
    main()