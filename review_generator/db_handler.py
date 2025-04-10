import pymongo
from bson import ObjectId
import json
from datetime import datetime

class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(MongoJSONEncoder, self).default(obj)

class DBHandler:
    def __init__(self, mongo_uri, database_name):
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[database_name]
        self.raw_reviews = self.db["raw_reviews"]
        self.product_reviews = self.db["product_reviews"]
        self.comparison_reviews = self.db["comparison_reviews"]
        self.search_queries = self.db["search_queries"]
    
    def get_all_search_queries(self):
        """
        Get all unique search queries from raw_reviews
        """
        return self.raw_reviews.distinct("search_query")
    
    def get_raw_reviews_by_query(self, search_query):
        """
        Get all raw reviews for a specific search query
        """
        return list(self.raw_reviews.find({"search_query": search_query}))
    
    def save_product_review(self, product_data):
        """
        Save a product review to the database
        """
        # Add timestamps
        now = datetime.now()
        product_data["createdAt"] = now
        product_data["updatedAt"] = now
        
        # Insert or update the product review
        result = self.product_reviews.update_one(
            {"productName": product_data["productName"], "productSearchString": product_data["productSearchString"]},
            {"$set": product_data},
            upsert=True
        )
        
        # Return the ID of the inserted/updated document
        if result.upserted_id:
            return result.upserted_id
        else:
            return self.product_reviews.find_one(
                {"productName": product_data["productName"], "productSearchString": product_data["productSearchString"]}
            )["_id"]
    
    def save_comparison_review(self, review_data):
        """
        Save a comparison review to the database
        """
        # Add timestamps
        now = datetime.now()
        review_data["createdAt"] = now
        review_data["updatedAt"] = now
        
        # Insert or update the comparison review
        result = self.comparison_reviews.update_one(
            {"reviewTitle": review_data["reviewTitle"]},
            {"$set": review_data},
            upsert=True
        )
        
        # Return the ID of the inserted/updated document
        if result.upserted_id:
            return result.upserted_id
        else:
            return self.comparison_reviews.find_one({"reviewTitle": review_data["reviewTitle"]})["_id"]
    
    def get_product_reviews_by_query(self, search_query):
        """
        Get all product reviews for a specific search query
        """
        return list(self.product_reviews.find({"productSearchString": search_query}))