from flask import Flask, render_template
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
import sys
import logging

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configure Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

def get_google_sheets_service():
    logging.info(f"Spreadsheet ID: {SPREADSHEET_ID}")
    
    if not CREDENTIALS_JSON:
        raise ValueError("GOOGLE_CREDENTIALS_JSON environment variable is required")
        
    try:
        import json
        import tempfile
        
        # Parse JSON
        try:
            creds_dict = json.loads(CREDENTIALS_JSON)
            logging.info("Successfully parsed credentials JSON")
        except json.JSONDecodeError as je:
            logging.error(f"Failed to parse credentials JSON: {je}")
            raise ValueError("Invalid JSON in credentials") from je
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            json.dump(creds_dict, temp_file)
            temp_path = temp_file.name
            logging.info(f"Wrote credentials to temporary file: {temp_path}")
        
        try:
            credentials = service_account.Credentials.from_service_account_file(
                temp_path, scopes=SCOPES)
            logging.info(f"Successfully loaded credentials for: {credentials.service_account_email}")
            return build('sheets', 'v4', credentials=credentials)
        finally:
            os.unlink(temp_path)  # Always clean up the temp file
            
        logging.info(f"Service account email: {credentials.service_account_email}")
        return build('sheets', 'v4', credentials=credentials)
    except Exception as e:
        logging.exception(f"Error loading credentials: {str(e)}")
        raise

@app.route('/')
def index():
    logging.info("Fetching home data...")
    return render_template('index.html')

@app.route('/races')
def races():
    logging.info("Fetching race data...")
    try:
        service = get_google_sheets_service()
        
        # Adjust range as needed
        RANGE_NAME = 'Sheet1!A1:Z'
        print(f"Fetching range: {RANGE_NAME}")
        
        sheet = service.spreadsheets()
        print("Making API request...")
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                  range=RANGE_NAME).execute()
        print("API request successful")
        values = result.get('values', [])
        
        if not values:
            return render_template('index.html', error='No data found.')
            
        headers = values[0]
        # Convert string boolean values to actual booleans
        processed_data = []
        for row in values[1:]:
            processed_row = []
            for cell in row:
                # Convert string boolean values to Python booleans
                if isinstance(cell, str):
                    cell_upper = cell.strip().upper()
                    if cell_upper in ['TRUE', 'FALSE']:
                        processed_row.append(cell_upper == 'TRUE')
                    else:
                        processed_row.append(cell)
                else:
                    processed_row.append(cell)
            processed_data.append(processed_row)
        return render_template('races.html', headers=headers, data=processed_data)
    except Exception as e:
        return render_template('races.html', error=str(e))

if __name__ == '__main__':
    # Only enable debug mode in development
    debug = os.environ.get('FLASK_ENV') == 'development'
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=debug)
