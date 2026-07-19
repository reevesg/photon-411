from flask import Flask, render_template, Response, abort
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
from markupsafe import Markup
import os
import sys
import logging
import calendar
import re
from datetime import datetime, timedelta
from icalendar import Calendar, Event
import pytz
import markdown

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

@app.template_filter('date_to_slug')
def date_to_slug_filter(date_str):
    d = parse_date(str(date_str))
    return d.strftime('%Y%m%d') if d else ''

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

        # Find next upcoming race
        today = datetime.now().date()
        next_race = None
        for row in values[1:]:
            if not row:
                continue
            d = parse_date(row[0])
            if d and d.date() >= today:
                name = row[3].strip() if len(row) > 3 and row[3].strip() else 'Race'
                next_race = {'slug': d.strftime('%Y%m%d'), 'name': name, 'date': d}
                break

        # Generate calendars for May through October
        calendars = [get_month_calendar(2026, month) for month in range(5, 11)]

        return render_template('races.html',
                             headers=headers,
                             data=values[1:],
                             calendars=calendars,
                             race_events=race_events,
                             next_race=next_race)

    except Exception as e:
        return render_template('races.html', error=str(e))

@app.route('/races.ics')
def races_ical():
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
            return Response('No data found.', status=404)

        headers = values[0]
        data = values[1:]
        
        # Create iCal calendar
        cal = Calendar()
        cal.add('prodid', '-//Sailing Photon Race Calendar//sailingphoton.com//')
        cal.add('version', '2.0')
        cal.add('x-wr-calname', 'Sailing Photon 2026 Races')
        cal.add('x-wr-caldesc', 'Race schedule for Sailing Photon')
        
        # Get column indices
        date_col = headers.index('Date') if 'Date' in headers else 0
        time_col = 2  # Column C - Dock Off
        name_col = 3  # Column D - Race name
        location_col = headers.index('Location') if 'Location' in headers else -1
        
        # Add events
        for row in data:
            if len(row) > date_col:
                date = parse_date(row[date_col])
                if date:
                    event = Event()
                    
                    # Event name
                    event_name = row[name_col] if len(row) > name_col else 'Race Event'
                    event.add('summary', event_name)
                    
                    # Event time - parse dock off time
                    event_time = row[time_col] if time_col >= 0 and len(row) > time_col else ''
                    
                    # Try to parse time (e.g., "9:00 AM" or "09:00")
                    if event_time:
                        try:
                            # Try parsing common time formats
                            for time_fmt in ['%I:%M %p', '%H:%M', '%I:%M%p']:
                                try:
                                    time_obj = datetime.strptime(event_time.strip(), time_fmt).time()
                                    start_datetime = datetime.combine(date.date(), time_obj)
                                    break
                                except ValueError:
                                    continue
                            else:
                                # If no time format worked, use 9 AM as default
                                start_datetime = datetime.combine(date.date(), datetime.strptime('09:00', '%H:%M').time())
                        except:
                            start_datetime = datetime.combine(date.date(), datetime.strptime('09:00', '%H:%M').time())
                    else:
                        # Default to 9 AM if no time specified
                        start_datetime = datetime.combine(date.date(), datetime.strptime('09:00', '%H:%M').time())
                    
                    # Set timezone to Central Time
                    central = pytz.timezone('America/Chicago')
                    start_datetime = central.localize(start_datetime)
                    
                    event.add('dtstart', start_datetime)
                    # Assume 4 hour duration for races
                    event.add('dtend', start_datetime + timedelta(hours=4))
                    
                    # Location
                    if location_col >= 0 and len(row) > location_col:
                        event.add('location', row[location_col])
                    
                    # Description with dock off time
                    description = f"Dock Off: {event_time}" if event_time else "Race Event"
                    event.add('description', description)
                    
                    # Add unique ID
                    event.add('uid', f"{date.strftime('%Y%m%d')}-{event_name.replace(' ', '-')}@sailingphoton.com")
                    
                    cal.add_component(event)
        
        # Return iCal file
        return Response(
            cal.to_ical(),
            mimetype='text/calendar',
            headers={
                'Content-Disposition': 'attachment; filename=sailing-photon-races.ics'
            }
        )
    
    except Exception as e:
        logging.error(f"Error generating iCal: {str(e)}")
        return Response(f'Error generating calendar: {str(e)}', status=500)

CREW_COLUMNS = [
    (7,  'Driver'),
    (8,  'Main'),
    (9,  'Bow'),
    (10, 'Pit'),
]
TRIMMER_COLUMNS = [11, 12, 13, 14]
EXTRA_COLUMNS   = [15, 16, 17, 18, 19, 20]

@app.route('/races/<date_str>')
def race_detail(date_str):
    try:
        race_date = datetime.strptime(date_str, '%Y%m%d')
    except ValueError:
        abort(404)

    try:
        service = get_google_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Races!A1:Z1000'
        ).execute()
        values = result.get('values', [])
    except Exception as e:
        logging.exception('Error fetching race detail')
        return render_template('race_detail.html', error=str(e))

    if not values:
        abort(404)

    # Collect all dated rows sorted by date
    dated_rows = []
    for r in values[1:]:
        if r and parse_date(r[0]):
            dated_rows.append((parse_date(r[0]).date(), r))
    dated_rows.sort(key=lambda x: x[0])

    row = None
    row_index = None
    for i, (d, r) in enumerate(dated_rows):
        if d == race_date.date():
            row = r
            row_index = i
            break

    if row is None:
        abort(404)

    def adjacent(i):
        if i is None or not (0 <= i < len(dated_rows)):
            return None
        d, r = dated_rows[i]
        def col_r(idx, default=''):
            return r[idx].strip() if len(r) > idx and r[idx].strip() else default
        return {'slug': d.strftime('%Y%m%d'), 'name': col_r(3, 'Race')}

    prev_race = adjacent(row_index - 1) if row_index > 0 else None
    next_race = adjacent(row_index + 1) if row_index < len(dated_rows) - 1 else None

    def col(i, default=''):
        return row[i].strip() if len(row) > i and row[i].strip() else default

    crew = [{'role': label, 'name': col(i), 'missing': not col(i)} for i, label in CREW_COLUMNS]
    trimmers = [col(i) for i in TRIMMER_COLUMNS]
    extras   = [col(i) for i in EXTRA_COLUMNS]

    race = {
        'date':     race_date,
        'weekday':  col(1),
        'dock_off': col(2),
        'name':     col(3, 'Race'),
        'type':     col(4),
        'location': col(5),
        'count':    col(6),
        'crew':     crew,
        'trimmers': trimmers,
        'extras':   extras,
    }
    return render_template('race_detail.html', race=race, date_str=date_str,
                           prev_race=prev_race, next_race=next_race)


CHECKLISTS = [
    {'slug': 'delivery',        'title': 'Delivery',        'filename': 'Delivery.md'},
    {'slug': 'dock-off',        'title': 'Dock Off',        'filename': 'Dock Off.md'},
    {'slug': 'gybing',          'title': 'Gybing',          'filename': 'Gybing.md'},
    {'slug': 'headsail-change', 'title': 'Headsail Change', 'filename': 'Headsail Change.md'},
    {'slug': 'jib-trim',        'title': 'Jib Trim',        'filename': 'Jib Trim.md'},
    {'slug': 'kite-douse',      'title': 'Kite Douse',      'filename': 'Kite Douse.md'},
    {'slug': 'kite-peel',       'title': 'Kite Peel',       'filename': 'Kite Peel.md'},
    {'slug': 'kite-set',        'title': 'Kite Set',        'filename': 'Kite Set.md'},
    {'slug': 'main-drop',       'title': 'Main Drop',       'filename': 'Main Drop.md'},
    {'slug': 'main-hoist',      'title': 'Main Hoist',      'filename': 'Main Hoist.md'},
    {'slug': 'main-trim',       'title': 'Main Trim',       'filename': 'Main Trim.md'},
    {'slug': 'man-overboard',   'title': 'Man Overboard',   'filename': 'Man Overboard.md'},
    {'slug': 'post-race',       'title': 'Post-Race',       'filename': 'Post-Race.md'},
    {'slug': 'pre-start',       'title': 'Pre-Start',       'filename': 'Pre-Start.md'},
    {'slug': 'reefing',         'title': 'Reefing',         'filename': 'Reefing.md'},
    {'slug': 'tacking',         'title': 'Tacking',         'filename': 'Tacking.md'},
]

CHECKLIST_DIR = os.path.join(os.path.dirname(__file__), 'checklists')

def _render_checklist_md(text):
    # Convert task list items to interactive checkboxes before markdown processing
    text = re.sub(r'^(\s*)- \[ \] ', r'\1- <input type="checkbox" class="task-check"> ', text, flags=re.MULTILINE)
    text = re.sub(r'^(\s*)- \[x\] ', r'\1- <input type="checkbox" class="task-check" checked> ', text, flags=re.MULTILINE)
    return Markup(markdown.markdown(text, extensions=['tables']))

@app.route('/reports/mac26-race-analysis')
def report_mac26_race_analysis():
    return render_template('reports/mac26-race-analysis.html')

@app.route('/reports/mac26-race-replay')
def report_mac26_race_replay():
    return render_template('reports/mac26-race-replay.html')

@app.route('/checklists')
def checklists_index():
    return render_template('checklists.html', checklists=CHECKLISTS)

@app.route('/checklists/<slug>')
def checklist_detail(slug):
    item = next((c for c in CHECKLISTS if c['slug'] == slug), None)
    if item is None:
        abort(404)
    path = os.path.join(CHECKLIST_DIR, item['filename'])
    with open(path, 'r') as f:
        content = _render_checklist_md(f.read())
    return render_template('checklist_detail.html', title=item['title'], content=content, slug=slug)


if __name__ == '__main__':
    # Only enable debug mode in development
    debug = os.environ.get('FLASK_ENV') == 'development'
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=debug)
