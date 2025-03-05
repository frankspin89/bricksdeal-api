import { createRoute, z } from '@hono/zod-openapi';

// Health check response schema
export const HealthResponseSchema = z.object({
  status: z.string().openapi({
    description: 'API status',
    example: 'ok',
  }),
  message: z.string().openapi({
    description: 'Status message',
    example: 'Bricks Deal API is running',
  }),
  version: z.string().openapi({
    description: 'API version',
    example: '1.0.0',
  }),
});

// Health check route
export const healthRoute = createRoute({
  method: 'get',
  path: '/',
  tags: ['Health'],
  summary: 'Health check endpoint',
  description: 'Returns the status of the API',
  responses: {
    200: {
      description: 'API is running',
      content: {
        'application/json': {
          schema: HealthResponseSchema,
        },
      },
    },
  },
}); 