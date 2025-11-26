#!/bin/bash
# Cloud Run Deployment Script for MyCase Scraper
# Usage: ./deploy.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ortega-473114"
REGION="us-central1"
SERVICE_NAME="mycase-scraper-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
GCS_BUCKET="mycase-sessions-ortega-473114"
GCS_PREFIX="playwright-profiles/mycase/"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MyCase Scraper - Cloud Run Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if required environment variables are set
if [ -z "$MYCASE_EMAIL" ] || [ -z "$MYCASE_PASSWORD" ]; then
    echo -e "${RED}Error: MYCASE_EMAIL and MYCASE_PASSWORD must be set${NC}"
    echo "Export them in your shell or add to .env file"
    exit 1
fi

echo -e "${YELLOW}Step 1: Building Docker image...${NC}"
gcloud builds submit --tag "${IMAGE_NAME}" --project "${PROJECT_ID}"
echo -e "${GREEN}✓ Image built successfully${NC}"
echo ""

echo -e "${YELLOW}Step 2: Deploying to Cloud Run...${NC}"
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_NAME}" \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars="MYCASE_EMAIL=${MYCASE_EMAIL},MYCASE_PASSWORD=${MYCASE_PASSWORD},PW_PROFILE_GCS_BUCKET=${GCS_BUCKET},PW_PROFILE_GCS_PREFIX=${GCS_PREFIX},PW_HEADLESS=true" \
    --project "${PROJECT_ID}"
echo -e "${GREEN}✓ Deployed successfully${NC}"
echo ""

echo -e "${YELLOW}Step 3: Configuring service account permissions...${NC}"
SA_EMAIL="$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format='value(spec.template.spec.serviceAccount)' \
    --project ${PROJECT_ID})"

if [ -z "$SA_EMAIL" ]; then
    SA_EMAIL="${PROJECT_ID}-compute@developer.gserviceaccount.com"
    echo "Using default compute service account: ${SA_EMAIL}"
fi

# Grant storage permissions
gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectViewer" \
    --project "${PROJECT_ID}" 2>/dev/null || echo "Permission already exists"

gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectAdmin" \
    --project "${PROJECT_ID}" 2>/dev/null || echo "Permission already exists"

echo -e "${GREEN}✓ Permissions configured${NC}"
echo ""

echo -e "${YELLOW}Step 4: Getting service URL...${NC}"
SERVICE_URL="$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format='value(status.url)' \
    --project ${PROJECT_ID})"
echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"
echo ""

echo -e "${YELLOW}Step 5: Testing deployment...${NC}"
echo "Health check:"
curl -s "${SERVICE_URL}/health" | python -m json.tool || echo "Health check failed"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Service URL: ${SERVICE_URL}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Upload authenticated profile:"
echo "   python scripts/upload_profile_to_gcs.py"
echo ""
echo "2. Test the API:"
echo "   curl ${SERVICE_URL}/config/validate"
echo ""
echo "3. View logs:"
echo "   gcloud run services logs read ${SERVICE_NAME} --region ${REGION}"
echo ""
echo "4. Monitor the service:"
echo "   https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}/metrics?project=${PROJECT_ID}"
