#!/bin/bash
# End-to-end Infrastructure Deployment Script
set -e
echo "Initializing Terraform..."
terraform init

echo "Applying IaC Terraform modules..."
terraform apply -auto-approve

echo "Deploying Cloud Build configurations..."
gcloud builds submit --config cloudbuild.yaml .
