# Bricks Deal API

This is the API for Bricks Deal, a platform for LEGO sets and minifigures database.

## Environment Variables

The API requires the following environment variables:

- `JWT_SECRET`: Secret key for JWT token generation and validation
- `ADMIN_USERNAME`: Username for admin access
- `ADMIN_PASSWORD`: Password for admin access
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID
- `CLOUDFLARE_ACCESS_KEY_ID`: Cloudflare access key ID
- `CLOUDFLARE_SECRET_ACCESS_KEY`: Cloudflare secret access key
- `CLOUDFLARE_DOMAIN`: Cloudflare domain for images
- `CLOUDFLARE_R2_BUCKET`: Cloudflare R2 bucket name
- `CLOUDFLARE_DATABASE_ID`: Cloudflare D1 database ID
- `OXYLABS_USERNAME`: Oxylabs username for web scraping
- `OXYLABS_PASSWORD`: Oxylabs password for web scraping
- `OXYLABS_ENDPOINT`: Oxylabs endpoint for web scraping
- `OXYLABS_PORTS`: Oxylabs ports for web scraping
- `DEEPSEEK_API_KEY`: DeepSeek API key for AI processing

## Development

To run the API in development mode:

```bash
npm run dev:env
```

This will load environment variables from the `.env` file and start the development server.

## Deployment

To deploy the API to Cloudflare Workers:

```bash
# Deploy to development environment
npm run deploy:dev

# Deploy to production environment
npm run deploy:prod
```

## API Documentation

The API documentation is available using OpenAPI/Swagger. When running the development server, you can access the documentation at:

```
http://localhost:8787/api-docs/docs
```

The OpenAPI JSON schema is available at:

```
http://localhost:8787/api-docs/openapi.json
```

### Available Endpoints

- `/`: Health check endpoint
- `/api/sets`: LEGO sets endpoints
- `/api/minifigs`: LEGO minifigures endpoints
- `/api/themes`: LEGO themes endpoints
- `/api-docs/docs`: Swagger UI for API documentation

## Testing

To run tests:

```bash
npm test
```

For test coverage:

```bash
npm run test:coverage
```

## Validation

The API validates environment variables on startup. In development mode, it will log warnings for missing variables but still run. In production mode, it will enforce stricter validation.
