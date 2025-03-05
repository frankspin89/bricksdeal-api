import { createRoute } from '@hono/zod-openapi';
import { z } from 'zod';
import { 
  SetSchema, 
  SetsListResponseSchema, 
  SetDetailResponseSchema, 
  ErrorResponseSchema 
} from '../schemas/sets';

// Get all sets route
export const getAllSetsRoute = createRoute({
  method: 'get',
  path: '/api/sets',
  tags: ['Sets'],
  summary: 'Get all sets',
  description: 'Retrieve a paginated list of all LEGO sets',
  request: {
    query: z.object({
      page: z.string().optional().openapi({
        description: 'Page number',
        example: '1',
      }),
      pageSize: z.string().optional().openapi({
        description: 'Number of items per page',
        example: '20',
      }),
      theme: z.string().optional().openapi({
        description: 'Filter by theme ID',
        example: '158',
      }),
      year: z.string().optional().openapi({
        description: 'Filter by release year',
        example: '2017',
      }),
      search: z.string().optional().openapi({
        description: 'Search term for set name',
        example: 'falcon',
      }),
    }),
  },
  responses: {
    200: {
      description: 'List of sets',
      content: {
        'application/json': {
          schema: SetsListResponseSchema,
        },
      },
    },
    500: {
      description: 'Server error',
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
    },
  },
});

// Get set by ID route
export const getSetByIdRoute = createRoute({
  method: 'get',
  path: '/api/sets/{setNum}',
  tags: ['Sets'],
  summary: 'Get set by ID',
  description: 'Retrieve details for a specific LEGO set by its set number',
  request: {
    params: z.object({
      setNum: z.string().openapi({
        description: 'Set number',
        example: '75192-1',
      }),
    }),
  },
  responses: {
    200: {
      description: 'Set details',
      content: {
        'application/json': {
          schema: SetDetailResponseSchema,
        },
      },
    },
    404: {
      description: 'Set not found',
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
    },
    500: {
      description: 'Server error',
      content: {
        'application/json': {
          schema: ErrorResponseSchema,
        },
      },
    },
  },
}); 