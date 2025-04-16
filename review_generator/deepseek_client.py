import requests
import time
import json

class DeepSeekClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    
    def generate_content(self, prompt, max_tokens=8000, model="deepseek-chat", temperature=0.7, max_retries=3):
        """
        Generate content using DeepSeek API
        """
        print(f"Generating content with DeepSeek API (model: {model}, max_tokens: {max_tokens})")
        
        # Add instruction about product name importance
        enhanced_prompt = (
            "IMPORTANT INSTRUCTION: When identifying products, you MUST use their complete and accurate names exactly as provided in the data. "
            "Do not abbreviate, shorten, or modify product names in any way. "
            "The full and correct product name is critical for proper identification and must be preserved exactly as given in the source data.\n\n" + prompt
        )
        
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": enhanced_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        for attempt in range(max_retries):
            try:
                print(f"API request attempt {attempt + 1}/{max_retries}")
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=data,
                    timeout=120  # Increase timeout to 2 minutes
                )
                
                print(f"API response status code: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        response_json = response.json()
                        content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                        print(f"Successfully received content (length: {len(content)})")
                        return content
                    except (KeyError, IndexError, json.JSONDecodeError) as e:
                        print(f"Error parsing API response: {e}")
                        print(f"Response content: {response.text[:500]}...")
                elif response.status_code == 429:
                    # Rate limit exceeded, wait and retry
                    wait_time = min(2 ** attempt, 60)  # Exponential backoff, max 60 seconds
                    print(f"Rate limit exceeded. Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                else:
                    print(f"API error: {response.status_code}")
                    print(f"Response content: {response.text[:500]}...")
                    
                    # If we get a 400 error, the prompt might be too long
                    if response.status_code == 400 and attempt < max_retries - 1:
                        print("Reducing prompt size for next attempt...")
                        # Reduce the prompt size by truncating the data portion
                        data_start = prompt.find("Here's the data:")
                        data_end = prompt.find("For each product", data_start)
                        if data_start > 0 and data_end > data_start:
                            # Reduce the data portion by 25% for each retry
                            reduction_factor = 0.75 ** (attempt + 1)
                            data_portion = prompt[data_start:data_end]
                            reduced_data_portion = data_portion[:int(len(data_portion) * reduction_factor)]
                            prompt = prompt[:data_start] + reduced_data_portion + prompt[data_end:]
                            data["messages"][0]["content"] = prompt
                            print(f"Reduced prompt length to {len(prompt)} characters")
                    
                    # If not a rate limit issue and we've tried reducing the prompt, break
                    if response.status_code != 429 and attempt == max_retries - 1:
                        break
            except requests.exceptions.RequestException as e:
                print(f"Request error: {e}")
                wait_time = min(2 ** attempt, 60)
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
        
        print("All API request attempts failed")
        return None