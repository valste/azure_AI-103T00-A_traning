#!/bin/bash

# Set variable values
subscription_id="Azure subscription 1"
resource_group="rg-valerian.stenske-5451"
location="swedencentral"
expiry_date="2028-01-01T00:00:00Z"

# Get random numbers to create unique resource names
unique_id=$((1 + RANDOM % 99999))

# Create a storage account in your Azure resource group
echo "Creating storage..."
az storage account create \
  --name "ai102form$unique_id" \
  --subscription "$subscription_id" \
  --resource-group "$resource_group" \
  --location "$location" \
  --sku Standard_LRS \
  --encryption-services blob \
  --default-action Allow \
  --allow-blob-public-access true \
  --only-show-errors \
  --output none

echo "Uploading files..."

# Get storage key without requiring jq
AZURE_STORAGE_KEY=$(az storage account keys list \
  --subscription "$subscription_id" \
  --resource-group "$resource_group" \
  --account-name "ai102form$unique_id" \
  --query "[?keyName=='key1'].value | [0]" \
  --output tsv)

# Create a container
az storage container create \
  --account-name "ai102form$unique_id" \
  --name sampleforms \
  --public-access blob \
  --auth-mode key \
  --account-key "$AZURE_STORAGE_KEY" \
  --output none

# Upload files from your local sample-forms folder to a container called sampleforms in the storage account
# Each file is uploaded as a blob
az storage blob upload-batch \
  -d sampleforms \
  -s ./sample-forms \
  --account-name "ai102form$unique_id" \
  --auth-mode key \
  --account-key "$AZURE_STORAGE_KEY" \
  --output none

# Set a variable value for future use
STORAGE_ACCT_NAME="ai102form$unique_id"

# Get a Shared Access Signature for the blobs in sampleforms
SAS_TOKEN=$(az storage container generate-sas \
  --account-name "ai102form$unique_id" \
  --name sampleforms \
  --expiry "$expiry_date" \
  --permissions rwl \
  --auth-mode key \
  --account-key "$AZURE_STORAGE_KEY" \
  --output tsv)

URI="https://$STORAGE_ACCT_NAME.blob.core.windows.net/sampleforms?$SAS_TOKEN"

# Print the generated Shared Access Signature URI
# This URI is used by Azure Storage to authorize access to the storage resource
echo "-------------------------------------"
echo "SAS URI: $URI"
