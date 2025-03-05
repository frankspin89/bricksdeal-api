import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { prettyJSON } from 'hono/pretty-json';
import type { Env } from 'hono';
import { createAuthRoutes } from './middleware/auth';
import { createAdminRoutes } from './routes/admin';
import { setsRouter } from './routes/sets';
import { minifigsRouter } from './routes/minifigs';
import { themesRouter } from './routes/themes';
import validateEnvironment from './validateEnv';
import { initEnv } from './config';
import { createOpenApiApp } from './openapi';

// Define custom environment
interface Variables {
  user?: {
    userId: string;
    username: string;
    role: string;
  };
  [key: string]: any;
}

// Create the main app with a simpler type definition
const app = new Hono<Env & { Variables: Variables }>();

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