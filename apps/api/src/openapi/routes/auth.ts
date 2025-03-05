import { createRoute } from '@hono/zod-openapi';
import { LoginRequestSchema, LoginResponseSchema, ErrorResponseSchema } from '../schemas/auth';

// Login route
export const loginRoute = createRoute({
  method: 'post',
  path: '/api/auth/login',
  tags: ['Authentication'],
  summary: 'Login to the application',
  description: 'Authenticate with username and password to receive a JWT token',
  request: {
    body: {
      content: {
        'application/json': {
          schema: LoginRequestSchema,
        },
      },
    },
  },
  responses: {
    200: {
      description: 'Login successful',
      content: {
        'application/json': {
          schema: LoginResponseSchema,
        },
      },
    },
    401: {
      description: 'Invalid credentials',
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
    },
  },
});

// Logout route
export const logoutRoute = createRoute({
  method: 'post',
  path: '/api/auth/logout',
  tags: ['Authentication'],
  summary: 'Logout from the application',
  description: 'Clear the authentication token',
  responses: {
    200: {
      description: 'Logout successful',
      content: {
        'application/json': {
          schema: LoginResponseSchema,
        },
      },
    },
  },
}); 