import sys
from review_generator.review_generator import ReviewGenerator

def main():
    # Initialize the review generator
    generator = ReviewGenerator()
    
    # Check if a specific query was provided
    if len(sys.argv) > 1:
        # Process the specific query
        search_query = sys.argv[1]
        print(f"Generating reviews for: {search_query}")
        generator.process_search_query(search_query)
    else:
        # Process all queries in the database
        print("No specific query provided. Generating reviews for all queries in the database.")
        generator.process_all_queries()
    
    print("Review generation complete.")

if __name__ == "__main__":
    main()