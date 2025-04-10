import argparse
from scraper.scraper import GoogleScraper
import config

def main():
    parser = argparse.ArgumentParser(description='Run the Google Search and Website Scraper')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--results', type=int, default=config.DEFAULT_RESULTS_LIMIT, 
                        help='Number of search results to process')
    parser.add_argument('--delay', type=float, default=config.DEFAULT_DELAY,
                        help='Delay between requests in seconds')
    
    args = parser.parse_args()
    
    print(f"Starting scraper for query: '{args.query}'")
    print(f"Processing up to {args.results} search results")
    print(f"Using delay of {args.delay} seconds between requests")
    
    scraper = GoogleScraper(delay=args.delay)
    results = scraper.run(args.query, args.results)
    
    print(f"Scraping complete. Processed {len(results)} websites.")

if __name__ == "__main__":
    main()