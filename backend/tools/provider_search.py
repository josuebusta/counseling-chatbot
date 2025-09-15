"""
Provider search functionality for finding PrEP providers.
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import pandas as pd
import time
from bs4 import BeautifulSoup
from typing import Dict
from .utils import translate_question


def search_provider(zip_code: str, language: str) -> Dict:
    """
    Searches for PrEP providers within 30 miles of the given ZIP code.
    """
    driver = None
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

        # Try to find Chrome binary automatically
        import subprocess
        import shutil

        chrome_paths = [
            '/usr/bin/google-chrome-stable',
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser',
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            shutil.which('google-chrome'),
            shutil.which('chromium-browser'),
            shutil.which('chrome')
        ]

        chrome_binary = None
        for path in chrome_paths:
            if path and shutil.which(path):
                chrome_binary = path
                break

        if chrome_binary:
            chrome_options.binary_location = chrome_binary
            print(f"Using Chrome binary: {chrome_binary}")
        else:
            print("Chrome binary not found, using system default")

        print("Setting up Chrome service...")
        # Try to find ChromeDriver automatically
        chromedriver_paths = [
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromedriver',
            shutil.which('chromedriver'),
            '/opt/homebrew/bin/chromedriver',  # macOS Homebrew
            '/usr/local/share/chromedriver'
        ]

        chromedriver_binary = None
        for path in chromedriver_paths:
            if path and shutil.which(path):
                chromedriver_binary = path
                break

        if chromedriver_binary:
            service = Service(executable_path=chromedriver_binary)
            print(f"Using ChromeDriver: {chromedriver_binary}")
        else:
            # Let webdriver-manager handle it automatically
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            print("Using webdriver-manager to download ChromeDriver")
        
        print("Creating Chrome driver...")
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Chrome driver created successfully")
        except Exception as e:
            print(f"Failed to create Chrome driver: {str(e)}")
            # Try to get more detailed error information
            print("Chrome version:",
                  subprocess.getoutput('google-chrome --version'))
            print("ChromeDriver version:",
                  subprocess.getoutput('chromedriver --version'))
            print("Chrome binary location:",
                  subprocess.getoutput('which google-chrome-stable'))
            print("ChromeDriver location:",
                  subprocess.getoutput('which chromedriver'))
            raise

        try:
            print(f"Navigating to preplocator.org for zip code {zip_code}...")
            driver.get("https://preplocator.org/")
            print("Page loaded successfully")
            time.sleep(5)

            print("Page source length:", len(driver.page_source))
            
            print("Looking for search box...")
            search_box = driver.find_element(By.CSS_SELECTOR,
                                             "input[type='search']")
            print("Search box found")
            
            search_box.clear()
            search_box.send_keys(zip_code)
            print(f"Entered zip code: {zip_code}")

            print("Looking for submit button...")
            submit_button = driver.find_element(By.CSS_SELECTOR,
                                                "button.btn[type='submit']")
            print("Submit button found")
            
            submit_button.click()
            print("Clicked submit button")
            
            time.sleep(5)
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            results = soup.find_all('div', class_='locator-results-item')
            
            extracted_data = []
            for result in results:
                name = (result.find('h3').text.strip()
                        if result.find('h3') else 'N/A')
                details = result.find_all('span')
                address = (details[0].text.strip()
                           if len(details) > 0 else 'N/A')
                phone = (details[1].text.strip()
                         if len(details) > 1 else 'N/A')
                distance_with_label = (details[2].text.strip()
                                       if len(details) > 2 else 'N/A')
                distance = (distance_with_label.replace(
                    'Distance from your location:', '').strip()
                    if distance_with_label != 'N/A' else 'N/A')
                extracted_data.append({
                    'Name': name,
                    'Address': address,
                    'Phone': phone,
                    'Distance': distance
                })

            if not extracted_data:
                return ("I couldn't find any providers in that area. "
                        "Would you like to try a different ZIP code?")

            df = pd.DataFrame(extracted_data)
            df['Distance'] = df['Distance'].str.replace(r'[^\d.]+', '',
                                                        regex=True)
            df['Distance'] = pd.to_numeric(df['Distance'], errors='coerce')
            filtered_df = df[df['Distance'] <= 30].nsmallest(5, 'Distance')

            if filtered_df.empty:
                return ("I couldn't find any providers within 30 miles of that "
                        "ZIP code. Would you like to try a different ZIP code?")

            formatted_results = "Here are the 5 closest providers to you:\n\n"
            for _, provider in filtered_df.iterrows():
                formatted_results += f"{provider['Name']}\n"
                formatted_results += f"- Address: {provider['Address']}\n"
                formatted_results += f"- Phone: {provider['Phone']}\n"
                formatted_results += f"- Distance: {provider['Distance']} miles\n\n"

            formatted_results += ("Would you like any additional information "
                                  "about these providers?")
            
            return translate_question(formatted_results, language)

        except Exception as e:
            print(f"Error during search: {str(e)}")
            print("Page source:", driver.page_source)
            raise
            
    except Exception as e:
        print(f"Error in search_provider: {str(e)}")
        return translate_question(
            f"I'm sorry, I couldn't find any providers near you. "
            f"Technical Error: {str(e)}", language)
    
    finally:
        if driver is not None:
            print("Closing Chrome driver...")
            driver.quit()
