import { z } from 'zod';

// Set schema
export const SetSchema = z.object({
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
  price: z.number().optional().openapi({
    description: 'Current price',
    example: 849.99,
  }),
  price_updated_at: z.string().optional().openapi({
    description: 'When the price was last updated',
    example: '2023-01-15T12:30:45Z',
  }),
});

// Sets list response schema
export const SetsListResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: true,
  }),
  sets: z.array(SetSchema).openapi({
    description: 'List of sets',
  }),
  total: z.number().openapi({
    description: 'Total number of sets',
    example: 120,
  }),
  page: z.number().openapi({
    description: 'Current page',
    example: 1,
  }),
  pageSize: z.number().openapi({
    description: 'Number of items per page',
    example: 20,
  }),
  totalPages: z.number().openapi({
    description: 'Total number of pages',
    example: 6,
  }),
});

// Set detail response schema
export const SetDetailResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: true,
  }),
  set: SetSchema.openapi({
    description: 'Set details',
  }),
});

// Error response schema
export const ErrorResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: false,
  }),
  error: z.string().openapi({
    description: 'Error message',
    example: 'Set not found',
  }),
}); 