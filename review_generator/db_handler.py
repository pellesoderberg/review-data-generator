import pymongo
from bson.objectid import ObjectId
import config
import json
from datetime import datetime

# Add a JSON encoder for MongoDB objects
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(MongoJSONEncoder, self).default(obj)

class DBHandler:
    def __init__(self, mongo_uri=None, database_name=None):
        # Use provided parameters or fall back to config values
        self.client = pymongo.MongoClient(mongo_uri or config.MONGO_URI)
        self.raw_db = self.client[database_name or config.DATABASE_NAME]
        self.raw_collection = self.raw_db[config.COLLECTION_NAME]
        
        # Use the new database for generated reviews
        self.reviews_db = self.client[config.REVIEWS_DATABASE_NAME]
        self.product_reviews = self.reviews_db[config.PRODUCT_REVIEWS_COLLECTION]
        self.comparison_reviews = self.reviews_db[config.COMPARISON_REVIEWS_COLLECTION]
    
    def get_raw_reviews_by_query(self, search_query):
        """
        Get raw reviews from the database by search query
        """
        return list(self.raw_collection.find({"search_query": search_query}))
    
    def save_product_review(self, product_data):
        """
        Save a product review to the database
        """
        # Check if product already exists
        existing = self.product_reviews.find_one({"productName": product_data["productName"]})
        if existing:
            # Update existing product
            product_data["_id"] = existing["_id"]
            self.product_reviews.replace_one({"_id": existing["_id"]}, product_data)
            return existing["_id"]
        else:
            # Insert new product
            result = self.product_reviews.insert_one(product_data)
            return result.inserted_id
    
    def get_product_reviews_by_query(self, search_query):
        """
        Get product reviews from the database by search query
        """
        return list(self.product_reviews.find({"productSearchString": search_query}))
    
    def save_comparison_review(self, review_data):
        """
        Save a comparison review to the database
        """
        # Check if review already exists
        existing = self.comparison_reviews.find_one({"slug": review_data["slug"]})
        if existing:
            # Update existing review
            review_data["_id"] = existing["_id"]
            self.comparison_reviews.replace_one({"_id": existing["_id"]}, review_data)
            return existing["_id"]
        else:
            # Insert new review
            result = self.comparison_reviews.insert_one(review_data)
            return result.inserted_id
    
    def get_all_search_queries(self):
        """
        Get all unique search queries from the raw reviews collection
        """
        # Use distinct to get unique search queries
        return self.raw_collection.distinct("search_query")
    
    def has_existing_reviews(self, search_query):
        """
        Check if product reviews already exist for a search query
        """
        # Check if there are any product reviews for this query
        existing_reviews = self.product_reviews.find_one({"productSearchString": search_query})
        return existing_reviews is not None
