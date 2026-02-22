from flask import Flask, render_template
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
import sys
import logging
import calendar
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

@app.template_filter('parse_date')
def parse_date_filter(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            return None

# Configure Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1APFhedHVWzf3fJRTOtUeTEId0Lp2dNPzBP91td5I5oQ'  # Hardcoded spreadsheet ID

def get_google_sheets_service():
    logging.info(f"Spreadsheet ID: {SPREADSHEET_ID}")
    
    credentials_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if not credentials_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON environment variable not found")
        
    try:
        credentials = service_account.Credentials.from_service_account_info(
            eval(credentials_json), scopes=SCOPES)
        logging.info(f"Successfully loaded credentials for: {credentials.service_account_email}")
        return build('sheets', 'v4', credentials=credentials)
    except Exception as e:
        logging.exception(f"Error loading credentials: {str(e)}")
        raise

@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

@app.route('/')
def index():
    logging.info("Fetching home data...")
    return render_template('index.html')

@app.route('/about')
def about():
    logging.info("Rendering about page...")
    return render_template('about.html')

@app.route('/crew')
def crew():
    logging.info("Rendering crew page...")
    return render_template('crew.html')

@app.route('/socials')
def socials():
    logging.info("Rendering socials page...")
    return render_template('socials.html')

@app.route('/blog')
def blog():
    logging.info("Rendering blog listing page...")
    return render_template('blog.html')

@app.route('/blog/new-for-2026')
def blog_new_for_2026():
    logging.info("Rendering blog post: New for 2026")
    return render_template('blog/new-for-2026.html')

def get_month_calendar(year, month):
    # Set first day of week to Monday (0 = Monday, 6 = Sunday)
    calendar.setfirstweekday(calendar.MONDAY)
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    return {
        'name': month_name,
        'weeks': cal,
        'year': year,
        'month': month
    }

def parse_date(date_str):
    if not date_str:
        return None
    # Try multiple date formats
    formats = ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%Y/%m/%d']
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except ValueError:
            continue
    return None

def get_race_events(data, headers):
    logging.info(f"Headers: {headers}")
    date_col = headers.index('Date') if 'Date' in headers else 0
    # Column C is index 2 (A=0, B=1, C=2)
    time_col = 2 if len(headers) > 2 else (headers.index('Dock Off') if 'Dock Off' in headers else -1)
    # Column D is index 3 (A=0, B=1, C=2, D=3)
    name_col = 3 if len(headers) > 3 else (headers.index('Race') if 'Race' in headers else 1)
    location_col = headers.index('Location') if 'Location' in headers else -1
    events = {}
    
    logging.info(f"Column indices - Date: {date_col}, Race: {name_col}, Time: {time_col}, Location: {location_col}")
    
    for row in data:
        if len(row) > date_col:
            date = parse_date(row[date_col])
            if date:
                event_name = row[name_col] if len(row) > name_col else 'Race Event'
                event_time = row[time_col] if time_col >= 0 and len(row) > time_col else ''
                event_location = row[location_col] if location_col >= 0 and len(row) > location_col else ''
                
                event_details = event_name
                if event_time:
                    event_details += f' - {event_time}'
                if event_location:
                    event_details += f' @ {event_location}'
                
                date_key = date.strftime('%Y-%m-%d')
                if date_key not in events:
                    events[date_key] = []
                events[date_key].append(event_details)
                logging.info(f"Added event: {date_key} -> {event_details}")
    
    logging.info(f"Total events: {len(events)}")
    return events

@app.route('/races')
def races():
    try:
        # Call the Sheets API
        service = get_google_sheets_service()
        spreadsheet = service.spreadsheets()
        result = spreadsheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Races!A1:Z1000'
        ).execute()
        values = result.get('values', [])

        if not values:
            return render_template('races.html', error='No data found.')

        headers = values[0]
        
        # Process race events
        race_events = get_race_events(values[1:], headers)
        
        # Generate calendars for May through October
        calendars = [get_month_calendar(2026, month) for month in range(5, 11)]

        return render_template('races.html', 
                             headers=headers, 
                             data=values[1:], 
                             calendars=calendars, 
                             race_events=race_events)

    except Exception as e:
        return render_template('races.html', error=str(e))

if __name__ == '__main__':
    # Only enable debug mode in development
    debug = os.environ.get('FLASK_ENV') == 'development'
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=debug)
