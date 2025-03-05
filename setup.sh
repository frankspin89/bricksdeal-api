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

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check for required tools
print_header "Checking required tools"

# Check for Node.js
if command_exists node; then
  NODE_VERSION=$(node -v)
  print_success "Node.js is installed: $NODE_VERSION"
else
  print_error "Node.js is not installed. Please install Node.js 18 or higher."
  exit 1
fi

# Check for npm
if command_exists npm; then
  NPM_VERSION=$(npm -v)
  print_success "npm is installed: $NPM_VERSION"
else
  print_error "npm is not installed. Please install npm."
  exit 1
fi

# Check for Python
if command_exists python3; then
  PYTHON_VERSION=$(python3 --version)
  print_success "Python is installed: $PYTHON_VERSION"
else
  print_warning "Python 3 is not installed. Some features may not work."
fi

# Check for pip
if command_exists pip3; then
  PIP_VERSION=$(pip3 --version | awk '{print $2}')
  print_success "pip is installed: $PIP_VERSION"
else
  print_warning "pip is not installed. Some features may not work."
fi

# Install dependencies
print_header "Installing dependencies"

# Install root dependencies
echo "Installing root dependencies..."
npm install
if [ $? -eq 0 ]; then
  print_success "Root dependencies installed successfully"
else
  print_error "Failed to install root dependencies"
  exit 1
fi

# Install API dependencies
echo "Installing API dependencies..."
cd apps/api
npm install
if [ $? -eq 0 ]; then
  print_success "API dependencies installed successfully"
else
  print_error "Failed to install API dependencies"
  exit 1
fi
cd ../..

# Install Web dependencies
echo "Installing Web dependencies..."
cd apps/web
npm install
if [ $? -eq 0 ]; then
  print_success "Web dependencies installed successfully"
else
  print_error "Failed to install Web dependencies"
  exit 1
fi
cd ../..

# Install Shared dependencies
echo "Installing Shared dependencies..."
cd packages/shared
npm install
if [ $? -eq 0 ]; then
  print_success "Shared dependencies installed successfully"
else
  print_error "Failed to install Shared dependencies"
  exit 1
fi
cd ../..

# Install UI dependencies (if they exist)
if [ -d "packages/ui" ]; then
  echo "Installing UI dependencies..."
  cd packages/ui
  npm install
  if [ $? -eq 0 ]; then
    print_success "UI dependencies installed successfully"
  else
    print_error "Failed to install UI dependencies"
    exit 1
  fi
  cd ../..
fi

# Install Python dependencies
if command_exists pip3; then
  echo "Installing Python dependencies..."
  cd tools/python
  pip3 install -e .
  if [ $? -eq 0 ]; then
    print_success "Python dependencies installed successfully"
  else
    print_error "Failed to install Python dependencies"
    exit 1
  fi
  cd ../..
fi

# Check for .env file
print_header "Checking environment configuration"

if [ -f ".env" ]; then
  print_success ".env file exists"
  
  # Check for required environment variables
  ENV_WARNINGS=0
  
  # Check JWT_SECRET
  if grep -q "JWT_SECRET=your-secret-key-change-in-production" .env; then
    print_warning "JWT_SECRET is using the default value. This is insecure for production environments."
    ENV_WARNINGS=$((ENV_WARNINGS+1))
  fi
  
  # Check ADMIN credentials
  if grep -q "ADMIN_USERNAME=admin" .env; then
    print_warning "ADMIN_USERNAME is using the default value. This is insecure for production environments."
    ENV_WARNINGS=$((ENV_WARNINGS+1))
  fi
  
  if grep -q "ADMIN_PASSWORD=password" .env || grep -q "ADMIN_PASSWORD=secure-password-for-admin" .env; then
    print_warning "ADMIN_PASSWORD is using a default value. This is insecure for production environments."
    ENV_WARNINGS=$((ENV_WARNINGS+1))
  fi
  
  # Check Cloudflare database ID
  if grep -q "CLOUDFLARE_DATABASE_ID=your-cloudflare-database-id" .env; then
    print_warning "CLOUDFLARE_DATABASE_ID is using a placeholder value. Please update it with your actual database ID."
    ENV_WARNINGS=$((ENV_WARNINGS+1))
  fi
  
  if [ $ENV_WARNINGS -eq 0 ]; then
    print_success "Environment variables look good"
  fi
else
  print_error ".env file does not exist. Please create one based on .env.example"
  exit 1
fi

# Run validation
print_header "Running validation"

# Validate API
echo "Validating API..."
cd apps/api
npm run validate
if [ $? -eq 0 ]; then
  print_success "API validation passed"
else
  print_warning "API validation failed. Please fix the issues before proceeding."
fi
cd ../..

# Validate Web
echo "Validating Web..."
cd apps/web
npm run validate
if [ $? -eq 0 ]; then
  print_success "Web validation passed"
else
  print_warning "Web validation failed. Please fix the issues before proceeding."
fi
cd ../..

# Run tests
print_header "Running tests"

# Test API
echo "Testing API..."
cd apps/api
npm test
if [ $? -eq 0 ]; then
  print_success "API tests passed"
else
  print_warning "API tests failed. Please fix the issues before proceeding."
fi
cd ../..

# Test Web
echo "Testing Web..."
cd apps/web
npm test
if [ $? -eq 0 ]; then
  print_success "Web tests passed"
else
  print_warning "Web tests failed. Please fix the issues before proceeding."
fi
cd ../..

print_header "Setup complete!"
echo -e "You can now run the following commands:"
echo -e "  ${GREEN}npm run dev${NC}      - Start the development server"
echo -e "  ${GREEN}npm run build${NC}    - Build the project for production"
echo -e "  ${GREEN}npm run test${NC}     - Run tests"
echo -e "  ${GREEN}npm run lint${NC}     - Run linting"
echo -e "\nHappy coding! 🚀" 