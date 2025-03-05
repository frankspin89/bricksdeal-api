# Bricks Deal

A LEGO catalog and browsing application with authentication and admin features.

## Project Structure

This is a monorepo containing:

- `apps/api`: Cloudflare Workers API
- `apps/web`: Astro frontend
- `packages/shared`: Shared TypeScript types and utilities
- `packages/ui`: Shared UI components
- `tools/python`: Python tools for data processing and extraction

## Features

- **Authentication**: JWT-based authentication for admin users
- **API**: RESTful API for LEGO sets, minifigures, and themes
- **Web Interface**: Browse LEGO sets, minifigures, and themes
- **Admin Interface**: Manage LEGO data through a protected admin interface
- **Data Processing**: Python tools for processing LEGO catalog data

## Pages

- **Home**: Landing page with overview of the application
- **Sets**: Browse LEGO sets with filtering and sorting
- **Minifigures**: Browse LEGO minifigures with filtering and sorting
- **Themes**: Browse LEGO themes with filtering and sorting
- **Admin**: Protected admin interface for managing data

## Getting Started

1. Run the setup script to install dependencies:

   ```bash
   ./setup.sh
   ```

2. Start the API server:

   ```bash
   cd apps/api && npm run dev
   ```

3. Start the web application:

   ```bash
   cd apps/web && npm run dev
   ```

4. Access the application:
   - Web: http://localhost:4321
   - API: http://localhost:8787

## Authentication

Default admin credentials:

- Username: `admin`
- Password: `admin123`

To authenticate, send a POST request to `/api/login` with the credentials.
The response will include a JWT token that should be included in the `Authorization` header for protected routes.

## API Endpoints

- `GET /api/sets`: Get all LEGO sets
- `GET /api/minifigs`: Get all LEGO minifigures
- `GET /api/themes`: Get all LEGO themes
- `POST /api/login`: Authenticate and get JWT token
- `GET /api/admin/dashboard`: Get admin dashboard data (protected)

## Development

### API

The API is built with Hono and includes the following endpoints:

- `/api/sets`: LEGO sets data
- `/api/minifigs`: LEGO minifigures data
- `/api/themes`: LEGO themes data
- `/api/search`: Search across all data types
- `/auth/*`: Authentication endpoints
- `/admin/*`: Protected admin endpoints

### Web

The web app is built with Astro and includes the following pages:

- `/`: Home page
- `/sets`: Browse sets
- `/minifigs`: Browse minifigures
- `/themes`: Browse themes
- `/search`: Search across all data
- `/admin/*`: Admin interface (protected)

### Running the Web Application

To run the web application locally:

```bash
cd apps/web
npm run dev
```

The web application will be available at http://localhost:4321.

### Mock Data

The web application is designed to work even when the API is not available. Each page that requires data from the API has been updated to include mock data when the API cannot be reached:

- **Sets Page**: Displays mock LEGO sets data
- **Minifigures Page**: Displays mock minifigures data
- **Themes Page**: Displays mock themes data
- **Search Page**: Provides mock search results based on the query
- **Admin Login**: In development mode, you can log in with username `admin` and password `admin` when the API is unavailable

This allows for frontend development to continue even when the backend services are not running or are still in development.

### Running the API

To run the API locally:

```bash
cd apps/api
npm run dev
```

The API will be available at http://localhost:8787.

### Python Tools

The project includes several Python tools for data extraction, processing, and management:

- `extract-catalog`: Extract catalog data from Brickset API
- `update-prices`: Update prices from BrickLink
- `setup-db`: Set up the database schema
- `export`: Export data from the database
- `clean`: Clean Cloudflare resources (R2 bucket and D1 database)
- `cleanup`: Clean up temporary files and directories
- `clean-backups`: Manage backup directories, keeping only the most recent ones
- `help`: Show detailed help and usage information

### Usage

Navigate to the tools directory and install the package:

```bash
cd tools/python
pip install -e .
```

Then you can use the commands:

```bash
bricks-deal extract-catalog
bricks-deal update-prices
bricks-deal setup-db
bricks-deal export
bricks-deal clean
bricks-deal cleanup
bricks-deal clean-backups
bricks-deal help
```

For a detailed overview of all commands and options, run:

```bash
bricks-deal help
```

### Backup Functionality

The tools include a secure backup system that:

1. Creates timestamped backups in a dedicated `backups` directory
2. Automatically redacts sensitive information from configuration files
3. Manages backup history to prevent disk space issues

To create a backup before cleaning:

```bash
bricks-deal clean --backup
bricks-deal cleanup --backup
```

To manage backup directories and keep only the most recent ones:

```bash
bricks-deal clean-backups --max-backups 5
```

For more details on the backup system and other maintenance commands, see the [Workflow Documentation](WORKFLOW.md).

## License

MIT
