import os
from dotenv import load_dotenv
from openai import OpenAI

def initialize_openai():
    # Load environment variables from .env file
    load_dotenv()

    # Get the API key from the environment variable
    api_key = os.getenv("OPENAI_API_KEY")

    # Check if the API key is set
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in the .env file.")

    # Create and return the OpenAI client
    return OpenAI(api_key=api_key)

# Initialize OpenAI and get the openai module
openai = initialize_openai()
