import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables. Please check your .env file.")

def generate_jwt_for_user(email: str, password: str):
    """
    Generate a valid JWT by authenticating with Supabase.
    This ensures the token is correctly signed and added to JWKS.
    """
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json"
    }
    
    data = json.dumps({
        "email": email,
        "password": password
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            access_token = result.get("access_token")
            user_id = result.get("user", {}).get("id")
            
            print(f"Successfully generated JWT for {email}")
            print(f"User ID: {user_id}")
            print("-" * 40)
            print("ACCESS TOKEN:")
            print(access_token)
            print("-" * 40)
            return access_token
            
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode()
        print(f"Failed to generate JWT. Status: {e.code}")
        print(f"Error: {error_msg}")
        return None

if __name__ == "__main__":
    # Replace with the actual password for the fisherman_example account
    EMAIL = "fishermen@gmail.com"
    PASSWORD = "123Fish"
    
    print(f"Attempting to generate token for {EMAIL}...")
    generate_jwt_for_user(EMAIL, PASSWORD)
