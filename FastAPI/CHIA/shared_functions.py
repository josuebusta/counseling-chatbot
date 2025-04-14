from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
from bs4 import BeautifulSoup
from typing import Dict

def search_provider(zip_code: str, language: str) -> Dict:
    """
    Searches for PrEP providers within 30 miles of the given ZIP code.
    """
    try:
        print("Initializing Chrome options...")
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless=new')  # Updated headless mode
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.binary_location = '/usr/bin/google-chrome-stable'

        print("Setting up Chrome service...")
        service = Service(executable_path='/usr/local/bin/chromedriver')
        
        print("Creating Chrome driver...")
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Chrome driver created successfully")
        except Exception as e:
            print(f"Failed to create Chrome driver: {str(e)}")
            # Try to get more detailed error information
            import subprocess
            print("Chrome version:", subprocess.getoutput('google-chrome --version'))
            raise

        # Rest of the search_provider function implementation...
        # (You'll need to copy the rest of the function implementation here)
        
    except Exception as e:
        print(f"Error in search_provider: {e}")
        return {"error": str(e)} 