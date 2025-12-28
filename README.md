# Google Sheets Data Viewer

A web application that displays data from a Google Spreadsheet.

## Prerequisites

1. Install Poetry (Python package manager):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

## Setup

1. Install dependencies:
```bash
poetry install
```

2. Set up Google Sheets API:
   - Go to Google Cloud Console
   - Create a new project
   - Enable Google Sheets API
   - Create credentials (Service Account)
   - Download the service account JSON key
   - Add the key contents to your `.env` file as `GOOGLE_CREDENTIALS_JSON`
   - Add your Google Sheets ID to `.env` as `SPREADSHEET_ID`

3. Configure environment:
   Create a `.env` file with the following variables:
   ```
   GOOGLE_CREDENTIALS_JSON=your_service_account_json
   SPREADSHEET_ID=your_spreadsheet_id
   FLASK_ENV=development  # Optional, enables debug mode
   ```

4. Run the application:
```bash
poetry run python app.py
```

5. Open http://localhost:8080 in your browser (or http://localhost:5001 for development)

## Development

- Add new dependencies: `poetry add package_name`
- Update dependencies: `poetry update`
- Run commands in virtual environment: `poetry run command`

## Docker

You can also run the application using Docker:

1. Build the container:
```bash
docker build -t photon .
```

2. Run the container:
```bash
docker run -p 8080:8080 \
  -e GOOGLE_CREDENTIALS_JSON='your_credentials_json' \
  -e SPREADSHEET_ID='your_spreadsheet_id' \
  photon
```

Or use Docker Compose:
```bash
docker-compose up
```

## Cloud Deployment

This application is configured for deployment to Google Cloud Run. See `cloudbuild.yaml` for deployment configuration.
