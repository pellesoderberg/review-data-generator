from review_generator.review_generator import ReviewGenerator

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python process_query.py 'search query'")
        sys.exit(1)
    
    search_query = sys.argv[1]
    generator = ReviewGenerator()
    generator.process_search_query(search_query)