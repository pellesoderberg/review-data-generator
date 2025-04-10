import argparse
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from pymongo import MongoClient

def connect_to_db():
    client = MongoClient(config.MONGO_URI)
    db = client[config.DATABASE_NAME]
    collection = db['raw_reviews']
    return collection

def list_queries(collection):
    """List all unique search queries in the database"""
    queries = collection.distinct('search_query')
    print(f"Found {len(queries)} unique search queries:")
    for i, query in enumerate(queries, 1):
        count = collection.count_documents({'search_query': query})
        print(f"{i}. '{query}' ({count} results)")

def view_results(collection, query=None, limit=5):
    """View results for a specific query or all results"""
    filter_dict = {'search_query': query} if query else {}
    
    results = collection.find(filter_dict).limit(limit)
    count = collection.count_documents(filter_dict)
    
    print(f"Showing {min(limit, count)} of {count} results:")
    
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"URL: {result.get('url')}")
        print(f"Domain: {result.get('domain')}")
        print(f"Title: {result.get('title')}")
        print(f"Search Query: {result.get('search_query')}")
        
        # Show a sample of content
        paragraphs = result.get('paragraphs', [])
        if paragraphs:
            print(f"\nContent Sample ({min(3, len(paragraphs))} of {len(paragraphs)} paragraphs):")
            for p in paragraphs[:3]:
                if len(p) > 150:
                    p = p[:147] + "..."
                print(f"- {p}")

def main():
    parser = argparse.ArgumentParser(description='View scraped data from MongoDB')
    parser.add_argument('--query', help='Filter results by search query')
    parser.add_argument('--limit', type=int, default=5, help='Limit number of results shown')
    parser.add_argument('--list-queries', action='store_true', help='List all unique search queries')
    
    args = parser.parse_args()
    
    collection = connect_to_db()
    
    if args.list_queries:
        list_queries(collection)
    else:
        view_results(collection, args.query, args.limit)

if __name__ == "__main__":
    main()