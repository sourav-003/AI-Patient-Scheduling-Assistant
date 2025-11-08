import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print(" GOOGLE_API_KEY not found in .env file.")
    print("Please make sure your .env file has your key.")
else:
    try:
        genai.configure(api_key=api_key)
        print(" API key configured. Fetching available models...\n")
        
        found_models = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                found_models = True
                model_name = m.name.split('/')[-1]
                print(f" Usable Model Name: {model_name}")

        if not found_models:
            print(" No models found for your API key.")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("This might be an invalid API key or a connection issue.")