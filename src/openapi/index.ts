import { swaggerUI } from '@hono/swagger-ui';
import { OpenAPIHono } from '@hono/zod-openapi';
import { openApiSetup } from './schema';
import { healthRoute } from './routes/health';
import type { D1Database, R2Bucket } from '@cloudflare/workers-types';

// Define custom environment
interface AppVariables {
  user?: {
    userId: string;
    username: string;
    role: string;
  };
  [key: string]: any;
}

// Define the environment bindings
interface Bindings {
  DB: D1Database;
  IMAGES: R2Bucket;
  JWT_SECRET: string;
  ADMIN_USERNAME: string;
  ADMIN_PASSWORD: string;
  CLOUDFLARE_ACCOUNT_ID: string;
  CLOUDFLARE_ACCESS_KEY_ID: string;
  CLOUDFLARE_SECRET_ACCESS_KEY: string;
  CLOUDFLARE_DOMAIN: string;
  CLOUDFLARE_R2_BUCKET: string;
  CLOUDFLARE_DATABASE_ID: string;
  OXYLABS_USERNAME: string;
  OXYLABS_PASSWORD: string;
  OXYLABS_ENDPOINT: string;
  OXYLABS_PORTS: string;
  DEEPSEEK_API_KEY: string;
  ENVIRONMENT?: string;
  [key: string]: any;
}

type AppEnv = {
  Variables: AppVariables;
  Bindings: Bindings;
};

// Create and configure the OpenAPI app
export const createOpenApiApp = () => {
  const openApiApp = openApiSetup() as OpenAPIHono<AppEnv>;

  // Register routes with OpenAPI
  openApiApp.openapi(healthRoute, (c) => {
    return c.json({
      status: 'ok',
      message: 'Bricks Deal API is running',
      version: '1.0.0',
    });
  });

  // Add Swagger UI
  openApiApp.get('/docs', swaggerUI({ url: '/openapi.json' }));

  return openApiApp;
}; 