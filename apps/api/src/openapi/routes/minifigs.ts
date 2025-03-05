import { createRoute } from '@hono/zod-openapi';
import { z } from '@hono/zod-openapi';
import { 
  minifigSchema, 
  minifigsListResponseSchema, 
  minifigDetailResponseSchema,
  errorResponseSchema 
} from '../schemas/minifigs';

// GET /api/minifigs
export const getAllMinifigsRoute = createRoute({
  method: 'get',
  path: '/api/minifigs',
  tags: ['Minifigs'],
  summary: 'Get all minifigs',
  description: 'Retrieve a paginated list of all LEGO minifigs',
  request: {
    query: z.object({
      limit: z.string().optional().openapi({
        description: 'Number of items per page',
        example: '50',
      }),
      offset: z.string().optional().openapi({
        description: 'Offset from the start',
        example: '0',
      }),
      search: z.string().optional().openapi({
        description: 'Search term for minifig name',
        example: 'luke',
      }),
    }),
  },
  responses: {
    200: {
      description: 'List of minifigs',
      content: {
        'application/json': {
          schema: minifigsListResponseSchema,
        },
      },
    },
    500: {
      description: 'Server error',
      content: {
        'application/json': {
          schema: errorResponseSchema,
        },
      },
    },
  },
});

// GET /api/minifigs/:fig_num
export const getMinifigByIdRoute = createRoute({
  method: 'get',
  path: '/api/minifigs/{fig_num}',
  tags: ['Minifigs'],
  summary: 'Get minifig by ID',
  description: 'Retrieve details for a specific LEGO minifig by its figure number',
  request: {
    params: z.object({
      fig_num: z.string().openapi({
        description: 'Minifig number',
        example: 'sw0001',
      }),
    }),
  },
  responses: {
    200: {
      description: 'Minifig details',
      content: {
        'application/json': {
          schema: minifigDetailResponseSchema,
        },
      },
    },
    404: {
      description: 'Minifig not found',
      content: {
        'application/json': {
          schema: errorResponseSchema,
        },
      },
    },
    500: {
      description: 'Server error',
      content: {
        'application/json': {
          schema: errorResponseSchema,
        },
      },
    },
  },
}); 