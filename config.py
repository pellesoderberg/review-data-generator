# Google Search API credentials
API_KEY = "AIzaSyCLm75M6nWTEUBUiDSKJpQ6elW__HZstqU"
CX = "81bf827bcd0cb437c"  # Replace with your custom search engine ID
DEFAULT_RESULTS_LIMIT = 8  # Default number of search results

# MongoDB connection setup
MONGO_URI = "mongodb+srv://pellesoederberg:EEZzvlcV10QFdzd9@mongodb-cluster.rn36cgo.mongodb.net/?retryWrites=true&w=majority&appName=mongodb-cluster"
DATABASE_NAME = "scraped_data"
COLLECTION_NAME = "raw_reviews"

# Database for generated reviews
REVIEWS_DATABASE_NAME = "reviews"
PRODUCT_REVIEWS_COLLECTION = "product_reviews"
COMPARISON_REVIEWS_COLLECTION = "comparison_reviews"

# Default scraper settings
DEFAULT_DELAY = 3
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Domains to exclude from scraping
EXCLUDED_DOMAINS = ['reddit.com', 'youtube.com', 'youtu.be']