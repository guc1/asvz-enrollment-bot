import requests
import time
from datetime import datetime, timedelta, timezone
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import json
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

def debug_print(message):
    """Helper function for debugging."""
    print(f"[DEBUG] {message}")

def perform_enrollment(asvz_id, password, base_url):
    """
    Performs the enrollment process using the provided ASVZ credentials and lesson URL.

    Args:
        asvz_id (str): The user's ASVZ ID.
        password (str): The user's ASVZ Password.
        base_url (str): The URL of the lesson to enroll in.

    Returns:
        bool: True if enrollment was successful, False otherwise.
    """

    print("[ENROLLMENT] Starting perform_enrollment function")

    # ============================
    # === Configuration Section ===
    # ============================

    # Enrollment API URL template
    enroll_url_template = 'https://schalter.asvz.ch/tn-api/api/Lessons/{lesson_id}/Enrollment'

    # ============================
    # ====== Helper Functions =====
    # ============================

    def get_bearer_token():
        """
        Retrieves the Bearer token by logging into the ASVZ account.

        Returns:
            str: The Bearer token if successful, None otherwise.
        """
        # URLs for login
        login_url = 'https://auth.asvz.ch/Account/Login?ReturnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3D55776bff-ef75-4c9d-9bdd-45e883ec38e0%26redirect_uri%3Dhttps%253A%252F%252Fschalter.asvz.ch%252Ftn%252Fassets%252Foidc-login-redirect.html%26response_type%3Did_token%2520token%26scope%3Dopenid%2520profile%2520tn-api%2520tn-apiext%2520tn-auth%2520tn-hangfire%26state%3Dfb63bd2a5a0e4b6c9827100d962f5372%26nonce%3D008106cdeeb6415287f6bce2c5c2c8b9'

        # Start a session to maintain cookies
        session = requests.Session()

        print(f"Starting login process for user: {asvz_id}")

        try:
            # Step 1: Fetch the login page and extract the verification token
            response = session.get(login_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            token_input = soup.find('input', {'name': '__RequestVerificationToken'})
            if not token_input:
                debug_print("Verification token not found on login page.")
                return None
            token = token_input['value']

            # Step 2: Submit the login form
            login_data = {
                'AsvzId': asvz_id,
                'Password': password,
                '__RequestVerificationToken': token
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' +
                              'AppleWebKit/537.36 (KHTML, like Gecko) ' +
                              'Chrome/119.0.0.0 Safari/537.36',
            }

            login_response = session.post(login_url, data=login_data, headers=headers)
            login_response.raise_for_status()

            # Check if login was successful by inspecting the redirect URL
            redirect_url = login_response.url
            print(f"Login Response URL: {redirect_url}")

            # Step 3: Extract access_token from the URL fragment
            parsed_url = urlparse(redirect_url)
            fragment_params = parse_qs(parsed_url.fragment)

            if 'access_token' in fragment_params:
                access_token = fragment_params['access_token'][0]
                print(f"Access Token: {access_token}")
                return access_token
            else:
                debug_print("No access token found. Check your credentials or login process.")
                return None

        except requests.RequestException as e:
            debug_print(f"HTTP Request failed during login: {e}")
            return None
        except Exception as e:
            debug_print(f"An unexpected error occurred during login: {e}")
            return None

    def extract_lesson_id(base_url):
        """
        Extracts the lesson_id from the base_url.

        Args:
            base_url (str): The base URL containing the lesson ID.

        Returns:
            str: The extracted lesson ID.
        """
        match = re.search(r'/lessons/(\d+)', base_url)
        if match:
            lesson_id = match.group(1)
            debug_print(f"Extracted lesson_id: {lesson_id}")
            return lesson_id
        else:
            debug_print("Failed to extract lesson_id from the base_url.")
            return None

    def fetch_lesson_data(api_url, bearer_token):
        """
        Fetches lesson data from the ASVZ API.

        Args:
            api_url (str): The API endpoint URL.
            bearer_token (str): The Bearer token for authorization.

        Returns:
            dict: The JSON data from the API response.
        """
        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' +
                          'AppleWebKit/537.36 (KHTML, like Gecko) ' +
                          'Chrome/119.0.0.0 Safari/537.36',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        }

        try:
            debug_print(f"Sending GET request to {api_url}")
            response = requests.get(api_url, headers=headers, timeout=10)
            debug_print(f"Received response with status code: {response.status_code}")

            if response.status_code != 200:
                debug_print(f"Failed to fetch data. Status Code: {response.status_code}")
                debug_print(f"Response Content: {response.text}")
                return None

            data = response.json()
            debug_print("Successfully retrieved JSON data from the API.")
            return data

        except requests.RequestException as e:
            debug_print(f"HTTP Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            debug_print(f"Failed to parse JSON: {e}")
            return None

    def extract_enrollment_start(data):
        """
        Extracts the enrollment start time from the lesson data.

        Args:
            data (dict): The JSON data from the API.

        Returns:
            datetime: The enrollment start time as a timezone-aware datetime object.
        """
        try:
            enrollment_from_str = data['data']['enrollmentFrom']
            debug_print(f"Extracted 'enrollmentFrom': {enrollment_from_str}")

            # Parse the ISO 8601 timestamp into a datetime object
            enrollment_start = datetime.fromisoformat(enrollment_from_str)
            debug_print(f"Parsed enrollment start time: {enrollment_start.isoformat()}")
            return enrollment_start
        except KeyError:
            debug_print("'enrollmentFrom' key not found in the data.")
            return None
        except ValueError as e:
            debug_print(f"Error parsing 'enrollmentFrom': {e}")
            return None

    def calculate_seconds_until_enrollment(enrollment_start):
        """
        Calculates the number of seconds until enrollment starts.

        Args:
            enrollment_start (datetime): The enrollment start time.

        Returns:
            int: Number of seconds until enrollment starts, or 0 if already started.
        """
        # Get current UTC time
        current_time = datetime.now(timezone.utc).astimezone(enrollment_start.tzinfo)
        debug_print(f"Current time: {current_time.isoformat()}")

        time_diff = enrollment_start - current_time
        debug_print(f"Time difference: {time_diff}")

        seconds_until = int(time_diff.total_seconds())
        debug_print(f"Seconds until enrollment: {seconds_until}")

        return seconds_until if seconds_until > 0 else 0

    def enroll_in_class(bearer_token, lesson_id):
        """
        Enrolls the user in the specified lesson.

        Args:
            bearer_token (str): The Bearer token for authorization.
            lesson_id (str): The ID of the lesson to enroll in.
        """
        enroll_url = enroll_url_template.format(lesson_id=lesson_id)
        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' +
                          'AppleWebKit/537.36 (KHTML, like Gecko) ' +
                          'Chrome/119.0.0.0 Safari/537.36',
        }

        print(f"Attempting to enroll in lesson {lesson_id} at {datetime.now()}...")
        try:
            response = requests.post(enroll_url, headers=headers, json={})
            if response.status_code == 201:  # 201 Created
                print("Successfully enrolled!")
                return True
            else:
                print(f"Failed to enroll. Status code: {response.status_code}")
                print("Response content:")
                print(response.text)
                return False
        except requests.RequestException as e:
            debug_print(f"HTTP Request failed during enrollment: {e}")
            return False

    def save_lesson_properties(data, filename='lesson_properties.json'):
        """
        Saves the lesson properties to a JSON file.

        Args:
            data (dict): The JSON data from the API.
            filename (str): The filename to save the data.
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            debug_print(f"Lesson properties saved to {filename}")
            return True
        except IOError as e:
            debug_print(f"Failed to write to file {filename}: {e}")
            return False

    # ============================
    # ========= Main Logic =========
    # ============================

    # Extract lesson_id from base_url
    lesson_id = extract_lesson_id(base_url)
    if not lesson_id:
        debug_print("Cannot proceed without a valid lesson ID.")
        return False

    # Construct API URL
    api_url = f'https://schalter.asvz.ch/tn-api/api/Lessons/{lesson_id}'
    debug_print(f"Constructed API URL: {api_url}")

    # Step 1: Log in and get the Bearer token
    bearer_token = get_bearer_token()
    if not bearer_token:
        debug_print("Failed to retrieve Bearer token. Exiting...")
        return False

    # Step 2: Fetch lesson data from the API
    data = fetch_lesson_data(api_url, bearer_token)
    if not data:
        debug_print("Failed to fetch lesson data. Exiting...")
        return False

    # Optionally, save the entire lesson data to a file
    if not save_lesson_properties(data):
        debug_print("Failed to save lesson properties. Exiting...")
        return False

    # Step 3: Extract the enrollment start time
    enrollment_start = extract_enrollment_start(data)
    if not enrollment_start:
        debug_print("Failed to extract enrollment start time. Exiting...")
        return False

    # Step 4: Calculate seconds until enrollment starts
    seconds_until = calculate_seconds_until_enrollment(enrollment_start)

    # Step 5: Determine action based on seconds_until
    if seconds_until > 60:
        # Wait until 60 seconds before enrollment time to update Bearer token
        wait_time = seconds_until - 60
        print(f"Waiting for {wait_time} seconds until 60 seconds before enrollment time...")
        time.sleep(wait_time)
        print(f"Reached 60 seconds before enrollment time at {datetime.now()}")

        # Update Bearer token
        bearer_token = get_bearer_token()
        if not bearer_token:
            debug_print("Failed to update Bearer token. Exiting...")
            return False

        # Re-fetch lesson data to ensure it's still valid
        data = fetch_lesson_data(api_url, bearer_token)
        if not data:
            debug_print("Failed to re-fetch lesson data after updating Bearer token. Exiting...")
            return False
        if not save_lesson_properties(data):
            debug_print("Failed to save lesson properties after updating Bearer token. Exiting...")
            return False
        enrollment_start = extract_enrollment_start(data)
        if not enrollment_start:
            debug_print("Failed to extract updated enrollment start time. Exiting...")
            return False
        seconds_until = calculate_seconds_until_enrollment(enrollment_start)

    elif 0 < seconds_until <= 60:
        # Less than or equal to 60 seconds until enrollment, update Bearer token immediately
        print("Less than or equal to 60 seconds until enrollment. Updating Bearer token immediately...")
        bearer_token = get_bearer_token()
        if not bearer_token:
            debug_print("Failed to update Bearer token. Exiting...")
            return False

    else:
        # Enrollment time has already passed or is now, proceed to enroll immediately
        print("Enrollment time has already started or passed. Proceeding to enrollment...")

    # Calculate updated seconds_until after potential Bearer token update
    if seconds_until > 60:
        # After updating Bearer token and re-fetching data
        enrollment_start = extract_enrollment_start(data)
        if not enrollment_start:
            debug_print("Failed to extract enrollment start time after updating Bearer token. Exiting...")
            return False
        seconds_until = calculate_seconds_until_enrollment(enrollment_start)

    # Step 6: Wait until the exact enrollment time with precise timing
    if seconds_until > 0:
        print(f"Waiting for {seconds_until} seconds until enrollment time...")
        target_time = enrollment_start
        while True:
            now = datetime.now(timezone.utc).astimezone(target_time.tzinfo)
            remaining = (target_time - now).total_seconds()
            if remaining <= 0:
                break
            sleep_duration = min(remaining, 0.1)  # Sleep in short intervals to maintain precision
            time.sleep(sleep_duration)
        print(f"Reached enrollment time at {datetime.now()}")

    # Step 7: Enroll in the class at the exact time
    success = enroll_in_class(bearer_token, lesson_id)
    print("[ENROLLMENT] perform_enrollment function completed")
    return success



