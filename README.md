# Google Sheets Data Viewer

A web application that displays data from a Google Spreadsheet.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up Google Sheets API:
   - Go to Google Cloud Console
   - Create a new project
   - Enable Google Sheets API
   - Create credentials (OAuth 2.0 Client ID)
   - Download the client configuration file as `credentials.json`

3. Run the application:
```bash
python app.py
```

4. Open http://localhost:5000 in your browser
