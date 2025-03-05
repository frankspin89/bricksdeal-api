import { createRoute, OpenAPIHono, z } from '@hono/zod-openapi';

// Define common schemas
export const ErrorSchema = z.object({
  error: z.string().openapi({
    description: 'Error message',
    example: 'An error occurred',
  }),
});

// Define common responses
export const UnauthorizedResponse = {
  description: 'Unauthorized',
  content: {
    'application/json': {
      schema: ErrorSchema,
    },
  },
};

export const NotFoundResponse = {
  description: 'Not Found',
  content: {
    'application/json': {
      schema: ErrorSchema,
    },
  },
};

export const BadRequestResponse = {
  description: 'Bad Request',
  content: {
    'application/json': {
      schema: ErrorSchema,
    },
  },
};

// Create OpenAPI instance
export const openApiSetup = () => {
  const openApiApp = new OpenAPIHono();

  // Define API info
  const openApiOptions = {
    openapi: '3.0.0',
    info: {
      title: 'Bricks Deal API',
      description: 'API for Bricks Deal - LEGO sets and minifigures database',
      version: '1.0.0',
      contact: {
        name: 'Bricks Deal Support',
        url: 'https://bricksdeal.com/support',
        email: 'support@bricksdeal.com',
      },
    },
    servers: [
      {
        url: 'http://localhost:8787',
        description: 'Local Development',
      },
      {
        url: 'https://api.bricksdeal.com',
        description: 'Production',
      },
    ],
  };

  openApiApp.doc('/openapi.json', openApiOptions);
  
  return openApiApp;
}; 