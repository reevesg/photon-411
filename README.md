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

### Prerequisites

1. Install Google Cloud SDK:
   ```bash
   # Visit https://cloud.google.com/sdk/docs/install for installation instructions
   gcloud init  # Initialize and select your project
   ```

2. Set up Google Cloud Project:
   - Create a new project or select existing one in Google Cloud Console
   - Enable required APIs:
     ```bash
     gcloud services enable cloudbuild.googleapis.com
     gcloud services enable run.googleapis.com
     gcloud services enable artifactregistry.googleapis.com
     ```

3. Set up Service Account:
   - Go to Google Cloud Console > IAM & Admin > Service Accounts
   - Create a new service account or select existing one
   - Download JSON credentials
   - Place credentials in `credentials/service_account.json`
   - Share your Google Spreadsheet with the service account email

### Deploy to Cloud Run

1. Ensure your code changes are committed:
   ```bash
   git add .
   git commit -m "Your commit message"
   git push
   ```

2. Deploy using Cloud Build:
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

   This method:
   - Creates reproducible builds with version history
   - Stores build artifacts in Container Registry
   - Supports automatic deployment triggers
   - Follows the deployment steps defined in `cloudbuild.yaml`
   - Can be integrated with CI/CD pipelines

   To set up automatic deployments:
   ```bash
   # Connect your repository to Cloud Build
   gcloud builds triggers create github \
     --repo-name=photon \
     --branch-pattern=main \
     --build-config=cloudbuild.yaml
   ```

### Service Accounts

The application uses several service accounts for different purposes:

1. **Application Service Account** (visible in IAM/Service Accounts)
   - Name: `srv-photon@photon-455210.iam.gserviceaccount.com`
   - Purpose: Access to Google Sheets API
   - Setup:
     1. Place credentials in `credentials/service_account.json`
     2. Share Google Spreadsheet with this account

2. **Cloud Run Service Account** (visible in IAM/Service Accounts)
   - Name: `317333230144-compute@developer.gserviceaccount.com`
   - Purpose: Running the application in Cloud Run
   - Managed by Google Cloud

3. **Cloud Build Service Account** (Google-managed, not visible in IAM/Service Accounts)
   - Name: `317333230144@cloudbuild.gserviceaccount.com`
   - Purpose: Building and deploying the application
   - Automatically created when Cloud Build API is enabled
   - Permissions managed through IAM roles

To view all service accounts and their roles:
```bash
# List visible service accounts
gcloud iam service-accounts list

# View all service accounts including Google-managed ones
gcloud projects get-iam-policy photon-455210 \
  --format='table(bindings.members,bindings.role)' | grep serviceAccount
```

### Custom Domain Setup

The application is configured to run at [sailingphoton.com](https://sailingphoton.com).

To update the domain configuration:

1. In Cloud Run console:
   ```bash
   # Map domain to Cloud Run service
   gcloud run domain-mappings create \
     --service=photon \
     --domain=sailingphoton.com \
     --region=us-central1
   
   # View domain mapping status and DNS records
   gcloud run domain-mappings describe \
     --domain=sailingphoton.com \
     --region=us-central1
   ```

2. In Squarespace DNS settings:
   - Add the DNS records provided by Cloud Run
   - Typically includes:
     - A CNAME record pointing to `ghs.googlehosted.com`
     - TXT records for domain verification

3. Wait for DNS propagation (can take up to 24-48 hours)

4. Verify SSL certificate provisioning:
   ```bash
   # Check certificate status
   gcloud run domain-mappings describe \
     --domain=sailingphoton.com \
     --region=us-central1 \
     --format='get(status.certificateProvisioningStatus)'
   ```

### Troubleshooting

1. View logs:
   ```bash
   gcloud run services logs read photon --region us-central1
   ```

2. Check service status:
   ```bash
   gcloud run services describe photon --region us-central1
   ```

3. Common issues:
   - 403 errors: Check service account permissions
   - 503 errors: Check application logs and environment variables
   - Build failures: Ensure all required APIs are enabled
