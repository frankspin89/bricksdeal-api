import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { prettyJSON } from 'hono/pretty-json';
import { createAuthRoutes } from './middleware/auth';
import { createAdminRoutes } from './routes/admin';
import { setsRouter } from './routes/sets';
import { minifigsRouter } from './routes/minifigs';
import { themesRouter } from './routes/themes';
import validateEnvironment from './validateEnv';
import { initEnv } from './config';
import { createOpenApiApp } from './openapi';

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

// Create the main app
const app = new Hono<AppEnv>();

// Middleware
app.use('*', logger());
app.use('*', prettyJSON());
app.use('*', cors({
  origin: ['http://localhost:3000', 'https://bricksdeal.com'],
  credentials: true,
}));

// Initialize environment variables
app.use('*', async (c, next) => {
  // Initialize environment variables from the worker's env
  initEnv(c.env as unknown as Record<string, string>);
  
  // Validate environment variables
  validateEnvironment();
  
  await next();
});

// Health check
app.get('/', (c) => {
  return c.json({
    status: 'ok',
    message: 'Bricks Deal API is running',
    version: '1.0.0',
  });
});

// Register routes
createAuthRoutes(app);
createAdminRoutes(app);
app.route('/api/sets', setsRouter);
app.route('/api/minifigs', minifigsRouter);
app.route('/api/themes', themesRouter);

// Register OpenAPI documentation
const openApiApp = createOpenApiApp();
app.route('/api-docs', openApiApp);

// Export for Cloudflare Workers
export default app; 