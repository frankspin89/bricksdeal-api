import { z } from '@hono/zod-openapi';

// Define the minifig schema
export const minifigSchema = z.object({
  fig_num: z.string().openapi({
    description: 'Minifig number',
    example: 'sw0001',
  }),
  name: z.string().openapi({
    description: 'Minifig name',
    example: 'Luke Skywalker',
  }),
  num_parts: z.number().optional().openapi({
    description: 'Number of parts',
    example: 4,
  }),
  img_url: z.string().optional().openapi({
    description: 'Image URL',
    example: 'https://images.bricksdeal.com/minifigs/sw0001.jpg',
  }),
});

// Define the minifigs list response schema
export const minifigsListResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: true,
  }),
  data: z.array(minifigSchema).openapi({
    description: 'List of LEGO minifigs',
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

// Define the minifig detail response schema
export const minifigDetailResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: true,
  }),
  data: minifigSchema.openapi({
    description: 'Minifig details',
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
    example: 'Minifig not found',
  }),
}); 