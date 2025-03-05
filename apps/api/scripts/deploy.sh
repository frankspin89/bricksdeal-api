#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section headers
print_header() {
  echo -e "\n${BLUE}==== $1 ====${NC}\n"
}

# Function to print success messages
print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

# Function to print warning messages
print_warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to print error messages
print_error() {
  echo -e "${RED}✗ $1${NC}"
}

# Check if .env file exists in the root directory
if [ ! -f "../../.env" ]; then
  print_error "No .env file found in the root directory. Please create one based on .env.example"
  exit 1
fi

print_header "Deploying API with environment variables"

# Load environment variables from .env file
set -a
source ../../.env
set +a

print_success "Environment variables loaded from .env file"

# Check for production environment
if [ "$1" == "production" ]; then
  ENV="production"
  print_warning "Deploying to PRODUCTION environment"
  
  # Confirm production deployment
  read -p "Are you sure you want to deploy to production? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_error "Deployment cancelled"
    exit 1
  fi
else
  ENV="development"
  print_success "Deploying to DEVELOPMENT environment"
fi

# Start wrangler with environment variables
print_header "Starting wrangler deployment"
npx wrangler deploy src/index.ts --env $ENV 