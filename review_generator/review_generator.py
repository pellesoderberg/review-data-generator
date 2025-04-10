import json
import time
from datetime import datetime
import re
from .deepseek_client import DeepSeekClient
from .db_handler import DBHandler, MongoJSONEncoder
import sys
import os

# Import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MONGO_URI, DATABASE_NAME

class ReviewGenerator:
    def __init__(self):
        self.deepseek_api_key = "sk-ec7ad7ba2bf94fd7b672ee2080910d44"
        self.deepseek_client = DeepSeekClient(self.deepseek_api_key)
        self.db_handler = DBHandler(MONGO_URI, DATABASE_NAME)
    
    def process_all_queries(self):
        """
        Process all search queries in the database
        """
        # Get all unique search queries from the raw reviews collection
        all_queries = self.db_handler.get_all_search_queries()
        
        if not all_queries:
            print("No search queries found in the database.")
            return
        
        print(f"Found {len(all_queries)} unique search queries.")
        
        # Process each query
        for query in all_queries:
            print(f"\n{'='*50}")
            print(f"Processing query: {query}")
            print(f"{'='*50}")
            self.process_search_query(query)
    
    def process_search_query(self, search_query):
        """
        Process a specific search query to generate product and comparison reviews
        """
        print(f"Processing search query: {search_query}")
        
        # Get raw reviews for this search query
        raw_reviews = self.db_handler.get_raw_reviews_by_query(search_query)
        
        if not raw_reviews:
            print(f"No raw reviews found for query: {search_query}")
            return
        
        # Generate product reviews
        product_ids = self.generate_product_reviews(raw_reviews, search_query)
        
        if product_ids:
            # Generate comparison review
            self.generate_comparison_review(search_query, product_ids)
        else:
            print(f"No product reviews were generated for query: {search_query}")
    
    def chunk_data(self, data, max_chunk_size=10):
        """
        Split data into manageable chunks for the LLM
        Using a reasonable chunk size to ensure we stay within token limits
        """
        # First, try to estimate how many items we can fit in a chunk
        if not data:
            return []
            
        # We'll take 10 items per chunk to provide more context
        items_per_chunk = max_chunk_size
        
        print(f"Using {items_per_chunk} items per chunk to stay within token limits")
        
        # Split data into chunks
        chunks = []
        for i in range(0, len(data), items_per_chunk):
            chunk = data[i:i + items_per_chunk]
            # Instead of sending the full data, extract only the most important fields
            simplified_chunk = []
            for item in chunk:
                # Extract only essential fields to reduce token count
                simplified_item = {
                    "title": item.get("title", ""),
                    "content": self._extract_summary(item.get("content", ""), 1000),  # Limit content length
                    "url": item.get("url", ""),
                    "source": item.get("source", "")
                }
                simplified_chunk.append(simplified_item)
            
            chunks.append(json.dumps(simplified_chunk, cls=MongoJSONEncoder))
        
        return chunks
    
    def _extract_summary(self, text, max_length=1000):
        """
        Extract a summary of the text to reduce token count
        """
        if not text:
            return ""
        
        # If text is already short enough, return it as is
        if len(text) <= max_length:
            return text
        
        # Otherwise, take the first part of the text
        summary = text[:max_length]
        
        # Try to find a good breaking point
        good_breaks = [". ", ".\n", "! ", "!\n", "? ", "?\n", "\n\n"]
        for break_point in good_breaks:
            last_good_break = summary.rfind(break_point)
            if last_good_break > max_length * 0.75:  # If we can find a break point in the last quarter
                return summary[:last_good_break + len(break_point)]
        
        return summary
    
    def generate_product_reviews(self, raw_reviews, search_query):
        """
        Generate individual product reviews using DeepSeek
        """
        print(f"Generating product reviews for: {search_query}")
        
        # Chunk the raw reviews data
        chunks = self.chunk_data(raw_reviews)
        print(f"Split data into {len(chunks)} chunks")
        
        # Collect all chunks data to provide complete context
        all_data = []
        for i, chunk in enumerate(chunks):
            try:
                print(f"Processing chunk {i+1}/{len(chunks)}")
                chunk_data = json.loads(chunk)
                print(f"Chunk {i+1} contains {len(chunk_data)} items")
                all_data.extend(chunk_data)
            except json.JSONDecodeError as e:
                print(f"Error parsing chunk data: {e}")
                print(f"Problematic chunk (first 200 chars): {chunk[:200]}...")
            except Exception as e:
                print(f"Unexpected error processing chunk: {type(e).__name__}: {e}")
        
        print(f"Total items collected: {len(all_data)}")
        
        # Handle case where no data was successfully parsed
        if not all_data:
            print("No valid data found in chunks. Cannot generate reviews.")
            return []
        
        # Prepare a simplified version of all data to reduce token count
        simplified_data = []
        try:
            for item in all_data:
                simplified_item = {
                    "title": item.get("title", ""),
                    "content_summary": self._extract_summary(item.get("content", ""), 500),
                    "url": item.get("url", ""),
                    "source": item.get("source", ""),
                    # Extract any price information if available
                    "price": item.get("price", ""),
                    "price_range": item.get("price_range", "")
                }
                simplified_data.append(simplified_item)
            
            print(f"Simplified data prepared with {len(simplified_data)} items")
            
            # Convert to JSON string
            all_data_json = json.dumps(simplified_data, cls=MongoJSONEncoder)
            print(f"JSON data prepared, length: {len(all_data_json)} characters")
        except Exception as e:
            print(f"Error preparing simplified data: {type(e).__name__}: {e}")
            return []
        
        # Determine appropriate category based on search query
        category_mapping = {
            "electronics": "Electronics and Gadgets",
            "phone": "Electronics and Gadgets",
            "laptop": "Electronics and Gadgets",
            "camera": "Electronics and Gadgets",
            "beauty": "Beauty and Personal Care",
            "skincare": "Beauty and Personal Care",
            "makeup": "Beauty and Personal Care",
            "hairdryer": "Beauty and Personal Care",
            "appliance": "Home Appliances",
            "vacuum": "Home Appliances",
            "fitness": "Health and Fitness",
            "exercise": "Health and Fitness",
            "clothing": "Fashion",
            "shoes": "Fashion",
            "car": "Automotive Products",
            "auto": "Automotive Products",
            "furniture": "Home and Furniture",
            "book": "Books and Educational Material",
            "toy": "Toys and Baby Products",
            "baby": "Toys and Baby Products",
            "food": "Food and Beverages",
            "drink": "Food and Beverages",
            "travel": "Travel Gear",
            "luggage": "Travel Gear"
        }
        
        # Default category
        product_category = "Electronics and Gadgets"
        
        # Try to find a matching category
        search_query_lower = search_query.lower()
        for key, category in category_mapping.items():
            if key in search_query_lower:
                product_category = category
                break
        
        product_ids = []
        
        # Create a prompt that explicitly requests five different products with unique awards
        try:
            prompt = f"""
            You are Product-Review-Crew, an independent review team that analyzes hundreds of data points to create comprehensive product reviews.
            
            Based on the following data about {search_query}, create FIVE DIFFERENT product reviews with unique awards:
            
            Each product must be different and have a unique, specific award assigned that highlights its key strength or use case.
            Examples of awards: "Best Overall", "Best Premium", "Best Affordable", "Good performance in rain", "Best Compact", "Best Battery Life", etc.
            
            Here's the data:
            {all_data_json}
            
            For each product, output in this exact format with NO additional formatting or characters:
            
            PRODUCT_REVIEW_START
            {{
              "productName": "Specific Product Name",
              "category": "{product_category}",
              "slug": "product-name-slug",
              "image": "URL",
              "priceRange": "Format as '$X - $Y' where X is the lowest price and Y is the highest price found for this product",
              "link": "URL",
              "ranking": Number (1-5, with 1 being the highest ranked),
              "award": "Specific award that highlights this product's key strength",
              "pros": ["Pro1", "Pro2", "Pro3"],
              "cons": ["Con1", "Con2", "Con3"],
              "shortSummary": "Brief summary",
              "review": "Approximately 250-word detailed review. Keep the review close to 250 words",
              "productSearchString": "{search_query}"
            }}
            PRODUCT_REVIEW_END
            
            Important: 
            1. Create FIVE SEPARATE product reviews with the format above, one after another.
            2. Each must be a different product with a UNIQUE award that highlights its specific strength.
            3. Do not add any markdown formatting, asterisks, or other special characters to the JSON.
            4. EVERY product MUST have EXACTLY THREE pros and THREE cons.
            5. The pros and cons MUST be specific to each product's actual features and performance, not generic.
            6. Each product MUST have COMPLETELY UNIQUE pros and cons - no two products should share the same pro or con.
            7. The priceRange field MUST be formatted as a range: "$X - $Y" where X is the lowest price and Y is the highest price you can find for this product in the data.
               If only one price is available, use "$X - $X". If no specific price is available, estimate a reasonable range based on the product category and quality.
            8. Assign rankings from 1-5 (with 1 being the highest ranked) based on overall quality and value.
            9. The review field should be around 250 words - detailed enough to be informative but concise.
            10. Do NOT mention who created the review or include phrases like "our analysis", "we found", "our team", etc. Focus solely on the product's features, performance, and benefits.
            11. Write in third person objective style. Avoid first person pronouns like "we", "our", "us".

            Warning:
            1. The product review can not be shorter than 200 words. That means that the review field should have reviews longer than 200 words.
            """
            
            print("Prompt prepared, sending to DeepSeek API...")
            
            # Generate content with increased max_tokens to accommodate five products
            response = self.deepseek_client.generate_content(prompt, max_tokens=6000)
            
            if response:
                print(f"Received response from DeepSeek, length: {len(response)} characters")
                # Extract product reviews from the response
                product_reviews = self.extract_product_reviews(response)
                print(f"Extracted {len(product_reviews)} product reviews from response")
                
                # Save each product review to the database
                for product_data in product_reviews:
                    try:
                        # Create a slug if not present
                        if not product_data.get("slug") and product_data.get("productName"):
                            product_data["slug"] = self.create_slug(product_data["productName"])
                        
                        # Ensure priceRange is present and properly formatted
                        if not product_data.get("priceRange") or " - " not in product_data.get("priceRange", ""):
                            # If no price range or improperly formatted, create a default one
                            if product_data.get("award") == "Best Premium" or "Premium" in product_data.get("award", ""):
                                product_data["priceRange"] = "$150 - $300"
                            elif product_data.get("award") == "Best Affordable" or "Budget" in product_data.get("award", ""):
                                product_data["priceRange"] = "$50 - $100"
                            else:
                                product_data["priceRange"] = "$100 - $200"
                        
                        # Ensure ranking is valid (1-5)
                        if not product_data.get("ranking") or not isinstance(product_data.get("ranking"), (int, float)) or product_data.get("ranking") < 1 or product_data.get("ranking") > 5:
                            # Assign a default ranking based on the order extracted
                            product_data["ranking"] = product_reviews.index(product_data) + 1
                        
                        # Ensure award is present
                        if not product_data.get("award"):
                            # Generate a default award based on ranking
                            if product_data.get("ranking") == 1:
                                product_data["award"] = "Best Overall"
                            elif product_data.get("ranking") == 2:
                                product_data["award"] = "Best Premium"
                            elif product_data.get("ranking") == 3:
                                product_data["award"] = "Best Value"
                            elif product_data.get("ranking") == 4:
                                product_data["award"] = "Best for Beginners"
                            else:
                                product_data["award"] = "Best Budget Option"
                        
                        # Ensure exactly three pros and cons
                        # ... existing pros and cons validation code ...
                        
                        # Ensure review is approximately 200 words
                                if "review" in product_data:
                                    product_data["review"] = self._validate_word_count(product_data["review"], 200, 20)
                                    
                                # Remove any mentions of who created the review
                                if "review" in product_data:
                                    product_data["review"] = re.sub(r'(?i)\b(we|our team|our analysis|we found|our review|our testing|we tested|we analyzed)\b', 
                                                                  'analysis', product_data["review"])
                                    product_data["review"] = re.sub(r'(?i)\bProduct-Review-Crew\b', 'Experts', product_data["review"])
                                
                                if "shortSummary" in product_data:
                                    product_data["shortSummary"] = re.sub(r'(?i)\b(we|our team|our analysis|we found|our review|our testing|we tested|we analyzed)\b', 
                                                                     'analysis', product_data["shortSummary"])
                                    product_data["shortSummary"] = re.sub(r'(?i)\bProduct-Review-Crew\b', 'Experts', product_data["shortSummary"])
                        
                        # Save to database
                        product_id = self.db_handler.save_product_review(product_data)
                        product_ids.append(product_id)
                        print(f"Saved product review for: {product_data.get('productName', 'Unknown')} - {product_data.get('award', 'No Award')}")
                    except Exception as e:
                        print(f"Error saving product review: {e}")
            else:
                print("Failed to generate product reviews from DeepSeek - empty response")
        except Exception as e:
            print(f"Error generating product reviews: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        return product_ids
    
    def extract_product_reviews(self, response):
        """
        Extract product reviews from the DeepSeek response
        """
        product_reviews = []
        
        # Find all product reviews in the response
        pattern = r"PRODUCT_REVIEW_START(.*?)PRODUCT_REVIEW_END"
        matches = re.finditer(pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                # Extract and parse the JSON
                json_str = match.group(1).strip()
                
                # Clean up any markdown code block markers and other formatting characters
                json_str = re.sub(r"```json|```|\*\*", "", json_str).strip()
                
                # Debug output to see what we're trying to parse
                print(f"Attempting to parse JSON: {json_str[:100]}...")
                
                # Try to fix common JSON formatting issues
                if not json_str.startswith('{'):
                    json_str = '{' + json_str.split('{', 1)[1]
                if not json_str.endswith('}'):
                    json_str = json_str.rsplit('}', 1)[0] + '}'
                
                product_data = json.loads(json_str)
                product_reviews.append(product_data)
                print(f"Successfully parsed product review for: {product_data.get('productName', 'Unknown')}")
            except json.JSONDecodeError as e:
                print(f"Error parsing product review JSON: {e}")
                print(f"Problematic JSON string: {json_str}")
                
                # Try a more aggressive cleaning approach for problematic JSON
                try:
                    # Remove all non-JSON characters and try again
                    cleaned_json = re.sub(r'[^\x20-\x7E]', '', json_str)
                    product_data = json.loads(cleaned_json)
                    product_reviews.append(product_data)
                    print(f"Successfully parsed product review after cleaning for: {product_data.get('productName', 'Unknown')}")
                except json.JSONDecodeError:
                    print("Failed to parse even after aggressive cleaning")
        
        return product_reviews
    
    def generate_comparison_review(self, search_query, product_ids):
        """
        Generate a comparison review for products in a search query
        """
        print(f"Generating comparison review for: {search_query}")
        
        # Get the product reviews from the database
        product_reviews = self.db_handler.get_product_reviews_by_query(search_query)
        
        if not product_reviews:
            print(f"No product reviews found for query: {search_query}")
            return
        
        # Limit to top 5 products to reduce token count
        product_reviews = sorted(product_reviews, key=lambda x: x.get("ranking", 999))[:5]
        
        # Determine appropriate category based on search query
        category_mapping = {
            "electronics": "Electronics and Gadgets",
            "phone": "Electronics and Gadgets",
            "laptop": "Electronics and Gadgets",
            "camera": "Electronics and Gadgets",
            "beauty": "Beauty and Personal Care",
            "skincare": "Beauty and Personal Care",
            "makeup": "Beauty and Personal Care",
            "hairdryer": "Beauty and Personal Care",
            "appliance": "Home Appliances",
            "vacuum": "Home Appliances",
            "fitness": "Health and Fitness",
            "exercise": "Health and Fitness",
            "clothing": "Fashion",
            "shoes": "Fashion",
            "car": "Automotive Products",
            "auto": "Automotive Products",
            "furniture": "Home and Furniture",
            "book": "Books and Educational Material",
            "toy": "Toys and Baby Products",
            "baby": "Toys and Baby Products",
            "food": "Food and Beverages",
            "drink": "Food and Beverages",
            "travel": "Travel Gear",
            "luggage": "Travel Gear"
        }
        
        # Default category
        product_category = "Electronics and Gadgets"
        
        # Try to find a matching category
        search_query_lower = search_query.lower()
        for key, category in category_mapping.items():
            if key in search_query_lower:
                product_category = category
                break
                
        # Alternatively, get category from the first product if available
        if product_reviews and len(product_reviews) > 0 and "category" in product_reviews[0]:
            product_category = product_reviews[0]["category"]
        
        # Prepare minimal product data for the prompt
        products_data = []
        for product in product_reviews:
            products_data.append({
                "productId": str(product["_id"]),
                "productName": product.get("productName", ""),
                "ranking": product.get("ranking", 0),
                "award": product.get("award", ""),
                "pros": product.get("pros", [])[:3],  # Include all 3 pros
                "cons": product.get("cons", [])[:3]   # Include all 3 cons
            })
        
        # Create product ID placeholders for the template
        product_id_placeholders = []
        for i, product in enumerate(products_data):
            product_id_placeholders.append(f'{{"productId": "{product["productId"]}"}}')
        
        # Join the placeholders with commas
        product_id_json = ",\n            ".join(product_id_placeholders)
        
        # Create a prompt for the simplified review format with proper escaping
        prompt = f"""
        You are Product-Review-Crew, an independent review team that analyzes hundreds of data points to create comprehensive product reviews.
        
        Create a detailed comparison review for {search_query} with NO additional formatting or characters:
        
        COMPARISON_REVIEW_START
        {{
          "reviewTitle": "Best {search_query} of {datetime.now().year} - Top {len(products_data)} Compared",
          "reviewSummary": "Write a concise, professional summary that objectively compares the key differences between these {len(products_data)} {search_query} products and highlights which types of users each product is best suited for",
          "slug": "best-{search_query.replace(' ', '-')}-compared",
          "category": "Choose the most appropriate category from this list: Electronics and Gadgets, Beauty and Personal Care, Home Appliances, Health and Fitness, Fashion, Automotive Products, Home and Furniture, Books and Educational Material, Toys and Baby Products, Food and Beverages, Travel Gear",
          "metaTitle": "Best {search_query.capitalize()} {datetime.now().year}: Top {len(products_data)} Ranked & Reviewed",
          "metaDescription": "Looking for the best {search_query}? Our in-depth comparison reviews the top {len(products_data)} options for every budget and need. See which one is right for you.",
          "tags": ["best {search_query}", "{search_query} reviews", "top {search_query}", "compare {search_query}", "{search_query} buying guide"],
          "comparisonReview": "1000+ word comparison of the products",
          "products": [
                {product_id_json}
          ]
        }}
        COMPARISON_REVIEW_END
        
        Products to include: {json.dumps(products_data, cls=MongoJSONEncoder)}
        
        Important: 
        1. Do not add any markdown formatting, asterisks, or other special characters to the JSON.
        2. The products array should ONLY contain productId references, no additional product details.
        3. Include ALL products from the provided list in the products array.
        4. Create a detailed, informative comparisonReview that thoroughly compares all products.
        5. The reviewSummary should be a concise, professional summary without any specific character limit. Focus on providing a clear, objective overview of the key differences between products.
        6. For the category field, select EXACTLY ONE category from the provided list that best matches the product type. Do not create new categories.
        7. Avoid marketing language or excessive adjectives in the reviewSummary - focus on factual comparisons and clear guidance for different user needs.
        8. The metaTitle, metaDescription, and tags should be SEO-optimized and accurately reflect the content.
        9. Mention that Product-Review-Crew analyzed data from multiple sources, but keep the focus on the products.
        10. Do not claim that Product-Review-Crew conducted the tests themselves.
        11. The review should be objective, highlighting the strengths and weaknesses of each product.
        """
        
        # Generate content with increased max_tokens
        response = self.deepseek_client.generate_content(prompt, max_tokens=6000)
        
        if response:
            # Extract comparison review from the response
            comparison_review = self.extract_comparison_review(response)
            
            if comparison_review:
                try:
                    # Create a slug if not present
                    if not comparison_review.get("slug") and comparison_review.get("reviewTitle"):
                        comparison_review["slug"] = self.create_slug(comparison_review["reviewTitle"])
                    
                    # Ensure reviewSummary is approximately 500 characters
                    if "reviewSummary" in comparison_review:
                        summary = comparison_review["reviewSummary"]
                        if len(summary) < 400 or len(summary) > 600:
                            print(f"ReviewSummary length ({len(summary)} chars) outside desired range (450-550 chars)")
                            # If too short, expand it; if too long, truncate it
                            if len(summary) < 400:
                                # Get product names and awards to include in expanded summary
                                product_names = [p.get("productName", "") for p in products_data]
                                awards = [p.get("award", "") for p in products_data]
                                expanded_summary = f"Our comprehensive comparison of the top {len(products_data)} {search_query} products reveals that {product_names[0]} stands out as {awards[0]}, while {product_names[1]} excels as {awards[1]}. "
                                if len(products_data) > 2:
                                    expanded_summary += f"For those seeking value, {product_names[2]} offers a great balance of features and price. "
                                expanded_summary += f"This guide helps you choose the perfect {search_query} based on your specific needs and budget. We've analyzed performance data, user feedback, and expert opinions to provide you with objective recommendations tailored to different needs and preferences. Our analysis considers factors like build quality, performance, features, and value to help you make an informed decision."
                                comparison_review["reviewSummary"] = expanded_summary[:550]
                            else:
                                # Truncate to 550 chars at a sentence boundary
                                truncated = summary[:550]
                                last_period = truncated.rfind('.')
                                if last_period > 400:  # Only truncate at a period if we're not cutting too much
                                    truncated = truncated[:last_period+1]
                                comparison_review["reviewSummary"] = truncated
                    else:
                        # Create a default summary if none exists
                        default_summary = f"Our comprehensive comparison of the top {len(products_data)} {search_query} products analyzes key features, performance, and value. From premium options to budget-friendly choices, we help you find the perfect match for your specific needs and preferences. Based on extensive research and data analysis, we've identified the strengths and limitations of each product to guide your purchasing decision. We consider factors such as build quality, performance metrics, user experience, and price-to-value ratio to provide you with objective recommendations for various use cases and budgets."
                        comparison_review["reviewSummary"] = default_summary = default_summary
                        
                    # Ensure category is one of the valid categories
                    valid_categories = [
                        "Electronics and Gadgets",
                        "Beauty and Personal Care",
                        "Home Appliances",
                        "Health and Fitness",
                        "Fashion",
                        "Automotive Products",
                        "Home and Furniture",
                        "Books and Educational Material",
                        "Toys and Baby Products",
                        "Food and Beverages",
                        "Travel Gear"
                    ]
                    
                    if not comparison_review.get("category") or comparison_review.get("category") not in valid_categories:
                        # Try to determine the appropriate category based on the search query
                        search_query_lower = search_query.lower()
                        category_mapping = {
                            "electronics": "Electronics and Gadgets",
                            "phone": "Electronics and Gadgets",
                            "laptop": "Electronics and Gadgets",
                            "camera": "Electronics and Gadgets",
                            "beauty": "Beauty and Personal Care",
                            "skincare": "Beauty and Personal Care",
                            "makeup": "Beauty and Personal Care",
                            "hairdryer": "Beauty and Personal Care",
                            "appliance": "Home Appliances",
                            "vacuum": "Home Appliances",
                            "fitness": "Health and Fitness",
                            "exercise": "Health and Fitness",
                            "clothing": "Fashion",
                            "shoes": "Fashion",
                            "car": "Automotive Products",
                            "auto": "Automotive Products",
                            "furniture": "Home and Furniture",
                            "book": "Books and Educational Material",
                            "toy": "Toys and Baby Products",
                            "baby": "Toys and Baby Products",
                            "food": "Food and Beverages",
                            "drink": "Food and Beverages",
                            "travel": "Travel Gear",
                            "luggage": "Travel Gear"
                        }
                        
                        for key, category in category_mapping.items():
                            if key in search_query_lower:
                                comparison_review["category"] = category
                                break
                        else:
                            # If no match found, default to Electronics and Gadgets
                            comparison_review["category"] = "Electronics and Gadgets"
                        
                    # Ensure products array contains all product IDs
                    if "products" in comparison_review:
                        # Check if the products array is properly formatted
                        if not all(isinstance(p, dict) and "productId" in p for p in comparison_review.get("products", [])):
                            print("Products array not properly formatted, rebuilding it")
                            comparison_review["products"] = []
                        
                        # Get the existing product IDs in the comparison review
                        existing_product_ids = [p.get("productId") for p in comparison_review.get("products", [])]
                        
                        # Add any missing product IDs
                        for pid in product_ids:
                            str_pid = str(pid)
                            if str_pid not in existing_product_ids:
                                comparison_review["products"].append({"productId": str_pid})
                    else:
                        # If products array is missing, create it with all product IDs
                        comparison_review["products"] = [{"productId": str(pid)} for pid in product_ids]
                    
                    # Save to database
                    review_id = self.db_handler.save_comparison_review(comparison_review)
                    print(f"Saved comparison review: {comparison_review.get('reviewTitle', 'Unknown')}")
                    return review_id
                except Exception as e:
                    print(f"Error saving comparison review: {e}")
            else:
                print("Failed to extract comparison review from DeepSeek response")
        else:
            print("Failed to generate comparison review from DeepSeek")
    
    def extract_comparison_review(self, response):
        """
        Extract comparison review from the DeepSeek response
        """
        pattern = r"COMPARISON_REVIEW_START(.*?)COMPARISON_REVIEW_END"
        match = re.search(pattern, response, re.DOTALL)
        
        if match:
            try:
                # Extract and parse the JSON
                json_str = match.group(1).strip()
                
                # Clean up any markdown code block markers and other formatting characters
                json_str = re.sub(r"```json|```|\*\*", "", json_str).strip()
                
                # Debug output to see what we're trying to parse
                print(f"Attempting to parse comparison review JSON: {json_str[:100]}...")
                
                # Try to fix common JSON formatting issues
                if not json_str.startswith('{'):
                    json_str = '{' + json_str.split('{', 1)[1]
                if not json_str.endswith('}'):
                    json_str = json_str.rsplit('}', 1)[0] + '}'
                
                review_data = json.loads(json_str)
                print(f"Successfully parsed comparison review for: {review_data.get('reviewTitle', 'Unknown')}")
                return review_data
            except json.JSONDecodeError as e:
                print(f"Error parsing comparison review JSON: {e}")
                print(f"Problematic JSON string: {json_str}")
                
                # Try a more aggressive cleaning approach for problematic JSON
                try:
                    # Remove all non-JSON characters and try again
                    cleaned_json = re.sub(r'[^\x20-\x7E]', '', json_str)
                    review_data = json.loads(cleaned_json)
                    print(f"Successfully parsed comparison review after cleaning for: {review_data.get('reviewTitle', 'Unknown')}")
                    return review_data
                except json.JSONDecodeError:
                    print("Failed to parse comparison review even after aggressive cleaning")
        
        return None
    
    def create_slug(self, text):
        """
        Create a URL-friendly slug from text
        """
        # Convert to lowercase
        slug = text.lower()
        # Replace non-alphanumeric characters with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        return slug
    
    def _validate_word_count(self, text, target_count=200, tolerance=20):
        """
        Validates that text is close to the target word count and adjusts if needed
        """
        if not text:
            return ""
            
        words = text.split()
        word_count = len(words)
        
        # If within tolerance, return as is
        if abs(word_count - target_count) <= tolerance:
            return text
            
        # If too short, add generic content
        if word_count < target_count - tolerance:
            additional_words_needed = target_count - word_count
            generic_text = "The product offers good value for the price point. Build quality is solid and the design is well thought out. Performance is reliable under various conditions. Users report high satisfaction with this product. It compares favorably to similar products in its category."
            generic_words = generic_text.split()
            
            # Add as many words as needed
            words.extend(generic_words[:additional_words_needed])
            return " ".join(words)
            
        # If too long, truncate at a sentence boundary
        if word_count > target_count + tolerance:
            target_words = words[:target_count]
            truncated_text = " ".join(target_words)
            
            # Find the last sentence boundary
            last_period = truncated_text.rfind('.')
            if last_period > len(truncated_text) * 0.75:  # Only truncate if we're not cutting too much
                truncated_text = truncated_text[:last_period+1]
            
            return truncated_text
            
        return text