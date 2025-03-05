import { createRoute } from '@hono/zod-openapi';
import { z } from '@hono/zod-openapi';
import { 
  themeSchema, 
  themesListResponseSchema, 
  themeDetailResponseSchema, 
  themeSetsResponseSchema,
  errorResponseSchema 
} from '../schemas/themes';

// GET /api/themes
export const getAllThemesRoute = createRoute({
  method: 'get',
  path: '/api/themes',
  tags: ['Themes'],
  summary: 'Get all themes',
  description: 'Retrieve a list of all LEGO themes',
  request: {
    query: z.object({
      parent_id: z.string().optional().openapi({
        description: 'Filter by parent theme ID',
        example: '123',
      }),
      search: z.string().optional().openapi({
        description: 'Search term for theme name',
        example: 'star',
      }),
    }),
  },
  responses: {
    200: {
      description: 'List of themes',
      content: {
        'application/json': {
          schema: themesListResponseSchema,
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

// GET /api/themes/:id
export const getThemeByIdRoute = createRoute({
  method: 'get',
  path: '/api/themes/{id}',
  tags: ['Themes'],
  summary: 'Get theme by ID',
  description: 'Retrieve details for a specific LEGO theme by its ID',
  request: {
    params: z.object({
      id: z.string().openapi({
        description: 'Theme ID',
        example: '158',
      }),
    }),
  },
  responses: {
    200: {
      description: 'Theme details',
      content: {
        'application/json': {
          schema: themeDetailResponseSchema,
        },
      },
    },
    404: {
      description: 'Theme not found',
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

// GET /api/themes/:id/sets
export const getThemeSetsRoute = createRoute({
  method: 'get',
  path: '/api/themes/{id}/sets',
  tags: ['Themes'],
  summary: 'Get sets by theme ID',
  description: 'Retrieve all LEGO sets belonging to a specific theme',
  request: {
    params: z.object({
      id: z.string().openapi({
        description: 'Theme ID',
        example: '158',
      }),
    }),
    query: z.object({
      limit: z.string().optional().openapi({
        description: 'Number of items per page',
        example: '50',
      }),
      offset: z.string().optional().openapi({
        description: 'Offset from the start',
        example: '0',
      }),
    }),
  },
  responses: {
    200: {
      description: 'List of sets in the theme',
      content: {
        'application/json': {
          schema: themeSetsResponseSchema,
        },
      },
    },
    404: {
      description: 'Theme not found',
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