import { z } from 'zod';

// Login request schema
export const LoginRequestSchema = z.object({
  username: z.string().openapi({
    description: 'Username for authentication',
    example: 'admin',
  }),
  password: z.string().openapi({
    description: 'Password for authentication',
    example: 'password',
  }),
});

// Login response schema
export const LoginResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the login was successful',
    example: true,
  }),
  message: z.string().openapi({
    description: 'Status message',
    example: 'Login successful',
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
    example: 'Invalid credentials',
  }),
});

// User payload schema
export const UserPayloadSchema = z.object({
  userId: z.string().openapi({
    description: 'User ID',
    example: '1',
  }),
  username: z.string().openapi({
    description: 'Username',
    example: 'admin',
  }),
  role: z.string().openapi({
    description: 'User role',
    example: 'admin',
  }),
}); 