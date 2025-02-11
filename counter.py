import json
import time
import os
import requests

STORAGE_PATH = '/data/counter.json'
KEY_NAME = 'counter'
LLM_SERVICE_URL = 'http://llm-service:8000/generate'

def initialize_counter():
    if not os.path.exists(STORAGE_PATH):
        with open(STORAGE_PATH, 'w') as f:
            json.dump({KEY_NAME: 0}, f)

def read_counter():
    with open(STORAGE_PATH, 'r') as f:
        data = json.load(f)
        return data[KEY_NAME]

def write_counter(value):
    with open(STORAGE_PATH, 'w') as f:
        json.dump({KEY_NAME: value}, f)
        f.flush()
        os.fsync(f.fileno())

def query_llm(prompt):
    try:
        payload = {
            "inputs": f"<start_of_turn>user\n{prompt}<end_of_turn>\n",
            "parameters": {
                "temperature": 0.90,
                "top_p": 0.95,
                "max_new_tokens": 128
            }
        }
        
        response = requests.post(LLM_SERVICE_URL, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error querying LLM service: {e}")
        return None

def main():
    initialize_counter()
    print("Starting counter program with LLM integration...")
    
    while True:
        try:
            current_value = read_counter()
            print(f"Current value: {current_value}")
            
            # Generate a prompt for the LLM based on the current counter value
            prompt = f"The counter is currently at {current_value}. Please generate a creative observation about this number."
            
            # Query the LLM
            llm_response = query_llm(prompt)
            if llm_response:
                print(f"LLM response: {llm_response}")
            
            # Increment value
            new_value = current_value + 1
            write_counter(new_value)
            print(f"Updated value to: {new_value}")
            
            time.sleep(10)
            
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()