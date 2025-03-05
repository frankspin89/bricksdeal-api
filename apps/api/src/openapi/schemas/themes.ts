import { z } from '@hono/zod-openapi';

// Define the theme schema
export const themeSchema = z.object({
  id: z.number().openapi({
    description: 'Theme ID',
    example: 158,
  }),
  name: z.string().openapi({
    description: 'Theme name',
    example: 'Star Wars',
  }),
  parent_id: z.number().nullable().optional().openapi({
    description: 'Parent theme ID',
    example: 123,
  }),
});

// Define the themes list response schema
export const themesListResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: true,
  }),
  data: z.array(themeSchema).openapi({
    description: 'List of LEGO themes',
  }),
});

// Define the theme detail response schema
export const themeDetailResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: true,
  }),
  data: themeSchema.openapi({
    description: 'Theme details',
  }),
});

// Define the theme sets response schema
export const themeSetsResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: true,
  }),
  data: z.array(z.object({
    set_num: z.string().openapi({
      description: 'Set number',
      example: '75192-1',
    }),
    name: z.string().openapi({
      description: 'Set name',
      example: 'Millennium Falcon',
    }),
    year: z.number().openapi({
      description: 'Release year',
      example: 2017,
    }),
    theme_id: z.number().openapi({
      description: 'Theme ID',
      example: 158,
    }),
    num_parts: z.number().optional().openapi({
      description: 'Number of parts',
      example: 7541,
    }),
    img_url: z.string().optional().openapi({
      description: 'Image URL',
      example: 'https://images.bricksdeal.com/sets/75192-1.jpg',
    }),
  })).openapi({
    description: 'List of sets in this theme',
  }),
  pagination: z.object({
    limit: z.number().openapi({
      description: 'Number of items per page',
      example: 50,
    }),
    offset: z.number().openapi({
      description: 'Offset from the start',
      example: 0,
    }),
    total: z.number().openapi({
      description: 'Total number of items',
      example: 100,
    }),
  }).openapi({
    description: 'Pagination information',
  }),
});

// Define the error response schema
export const errorResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: false,
  }),
  error: z.string().openapi({
    description: 'Error message',
    example: 'Theme not found',
  }),
}); 