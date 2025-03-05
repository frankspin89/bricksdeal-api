import { swaggerUI } from '@hono/swagger-ui';
import { OpenAPIHono } from '@hono/zod-openapi';
import { z } from '@hono/zod-openapi';
import { createRoute } from '@hono/zod-openapi';
import { Context } from 'hono';
import { AppEnv } from '../types';

// Import routes
import { loginRoute, logoutRoute } from './routes/auth';
import { getAllSetsRoute, getSetByIdRoute } from './routes/sets';
import { getAllThemesRoute, getThemeByIdRoute, getThemeSetsRoute } from './routes/themes';
import { getAllMinifigsRoute, getMinifigByIdRoute } from './routes/minifigs';

// Import handlers
import { 
  healthHandler, 
  loginHandler, 
  logoutHandler, 
  getAllSetsHandler, 
  getSetByIdHandler,
  getAllThemesHandler,
  getThemeByIdHandler,
  getThemeSetsHandler,
  getAllMinifigsHandler,
  getMinifigByIdHandler
} from './handlers';

// Define the health response schema
const healthResponseSchema = z.object({
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

// Define schemas for authentication
const loginRequestSchema = z.object({
  username: z.string().openapi({
    description: 'Username for authentication',
    example: 'admin',
  }),
  password: z.string().openapi({
    description: 'Password for authentication',
    example: 'password',
  }),
});

const loginSuccessResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the login was successful',
    example: true,
  }),
  message: z.string().openapi({
    description: 'Status message',
    example: 'Login successful',
  }),
});

const errorResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: false,
  }),
  error: z.string().openapi({
    description: 'Error message',
    example: 'Invalid credentials',
  }),
});

// Define schemas for sets
const setSchema = z.object({
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

const setsListResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: true,
  }),
  sets: z.array(setSchema).openapi({
    description: 'List of LEGO sets',
  }),
  total: z.number().openapi({
    description: 'Total number of sets',
    example: 1,
  }),
  page: z.number().openapi({
    description: 'Current page number',
    example: 1,
  }),
  pageSize: z.number().openapi({
    description: 'Number of items per page',
    example: 20,
  }),
  totalPages: z.number().openapi({
    description: 'Total number of pages',
    example: 1,
  }),
});

const setDetailResponseSchema = z.object({
  success: z.boolean().openapi({
    description: 'Whether the operation was successful',
    example: true,
  }),
  set: setSchema.openapi({
    description: 'LEGO set details',
  }),
});

/**
 * Creates and configures the OpenAPI application
 * @returns OpenAPIHono instance with routes and Swagger UI
 */
export function createOpenApiApp() {
  const openApiApp = new OpenAPIHono<AppEnv>();

  // Health route
  openApiApp.openapi(
    createRoute({
      method: 'get',
      path: '/health',
      tags: ['Health'],
      summary: 'Health check endpoint',
      description: 'Returns the status of the API',
      responses: {
        200: {
          description: 'API is healthy',
          content: {
            'application/json': {
              schema: healthResponseSchema,
            },
          },
        },
      },
    }),
    (c) => c.json({
      status: 'ok',
      message: 'Bricks Deal API is running',
      version: '1.0.0',
    })
  );

  // Authentication routes
  openApiApp.openapi(
    createRoute({
      method: 'post',
      path: '/api/auth/login',
      tags: ['Authentication'],
      summary: 'Login to the application',
      description: 'Authenticate with username and password to receive a JWT token',
      request: {
        body: {
          content: {
            'application/json': {
              schema: loginRequestSchema,
            },
          },
        },
      },
      responses: {
        200: {
          description: 'Login successful',
          content: {
            'application/json': {
              schema: loginSuccessResponseSchema,
            },
          },
        },
        401: {
          description: 'Invalid credentials',
          content: {
            'application/json': {
              schema: errorResponseSchema,
            },
          },
        },
      },
    }),
    async (c) => {
      // In a real implementation, we would validate credentials
      // For now, just return a success response
      return c.json({
        success: true,
        message: 'Login successful',
      }, 200);
    },
    // Add validation error handler
    (result, c) => {
      if (!result.success) {
        return c.json({
          success: false,
          error: 'Invalid request format',
        }, 401);
      }
    }
  );

  openApiApp.openapi(
    createRoute({
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
              schema: loginSuccessResponseSchema,
            },
          },
        },
      },
    }),
    (c) => c.json({
      success: true,
      message: 'Logged out successfully',
    }, 200)
  );

  // Sets routes
  openApiApp.openapi(
    createRoute({
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
              schema: setsListResponseSchema,
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
    }),
    async (c) => {
      try {
        // In a real implementation, we would fetch sets from the database
        // For now, just return a mock response
        return c.json({
          success: true,
          sets: [
            {
              set_num: '75192-1',
              name: 'Millennium Falcon',
              year: 2017,
              theme_id: 158,
              num_parts: 7541,
              img_url: 'https://images.bricksdeal.com/sets/75192-1.jpg',
              price: 849.99,
              price_updated_at: '2023-01-15T12:30:45Z',
            }
          ],
          total: 1,
          page: 1,
          pageSize: 20,
          totalPages: 1,
        }, 200);
      } catch (error) {
        return c.json({
          success: false,
          error: 'Server error',
        }, 500);
      }
    }
  );

  openApiApp.openapi(
    createRoute({
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
              schema: setDetailResponseSchema,
            },
          },
        },
        404: {
          description: 'Set not found',
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
    }),
    async (c) => {
      try {
        const setNum = c.req.param('setNum');
        
        // In a real implementation, we would fetch the set from the database
        // For now, just return a mock response
        return c.json({
          success: true,
          set: {
            set_num: setNum,
            name: 'Millennium Falcon',
            year: 2017,
            theme_id: 158,
            num_parts: 7541,
            img_url: 'https://images.bricksdeal.com/sets/75192-1.jpg',
            price: 849.99,
            price_updated_at: '2023-01-15T12:30:45Z',
          },
        }, 200);
      } catch (error) {
        // Check if it's a not found error
        if ((error as any)?.status === 404) {
          return c.json({
            success: false,
            error: 'Set not found',
          }, 404);
        }
        
        // Otherwise, it's a server error
        return c.json({
          success: false,
          error: 'Server error',
        }, 500);
      }
    }
  );

  // Themes routes
  openApiApp.openapi(
    getAllThemesRoute,
    async (c) => {
      try {
        const { parent_id, search } = c.req.query();
        
        // For documentation purposes only
        return c.json({
          success: true,
          data: [
            {
              id: 158,
              name: 'Star Wars',
              parent_id: null,
            },
            {
              id: 246,
              name: 'Harry Potter',
              parent_id: null,
            }
          ],
        }, 200);
      } catch (error) {
        return c.json({
          success: false,
          error: 'Server error',
        }, 500);
      }
    }
  );

  openApiApp.openapi(
    getThemeByIdRoute,
    async (c) => {
      try {
        const id = c.req.param('id');
        
        // For documentation purposes only
        return c.json({
          success: true,
          data: {
            id: parseInt(id),
            name: 'Star Wars',
            parent_id: null,
          },
        }, 200);
      } catch (error) {
        return c.json({
          success: false,
          error: 'Theme not found',
        }, 404);
      }
    }
  );

  openApiApp.openapi(
    getThemeSetsRoute,
    async (c) => {
      try {
        const id = c.req.param('id');
        const { limit = '50', offset = '0' } = c.req.query();
        
        // For documentation purposes only
        return c.json({
          success: true,
          data: [
            {
              set_num: '75192-1',
              name: 'Millennium Falcon',
              year: 2017,
              theme_id: parseInt(id),
              num_parts: 7541,
              img_url: 'https://images.bricksdeal.com/sets/75192-1.jpg',
            }
          ],
          pagination: {
            limit: parseInt(limit),
            offset: parseInt(offset),
            total: 1,
          },
        }, 200);
      } catch (error) {
        if ((error as any)?.status === 404) {
          return c.json({
            success: false,
            error: 'Theme not found',
          }, 404);
        }
        
        return c.json({
          success: false,
          error: 'Server error',
        }, 500);
      }
    }
  );

  // Minifigs routes
  openApiApp.openapi(
    getAllMinifigsRoute,
    async (c) => {
      try {
        const { limit = '50', offset = '0', search } = c.req.query();
        
        // For documentation purposes only
        return c.json({
          success: true,
          data: [
            {
              fig_num: 'sw0001',
              name: 'Luke Skywalker',
              num_parts: 4,
              img_url: 'https://images.bricksdeal.com/minifigs/sw0001.jpg',
            }
          ],
          pagination: {
            limit: parseInt(limit),
            offset: parseInt(offset),
            total: 1,
          },
        }, 200);
      } catch (error) {
        return c.json({
          success: false,
          error: 'Server error',
        }, 500);
      }
    }
  );

  openApiApp.openapi(
    getMinifigByIdRoute,
    async (c) => {
      try {
        const fig_num = c.req.param('fig_num');
        
        // For documentation purposes only
        return c.json({
          success: true,
          data: {
            fig_num: fig_num,
            name: 'Luke Skywalker',
            num_parts: 4,
            img_url: 'https://images.bricksdeal.com/minifigs/sw0001.jpg',
          },
        }, 200);
      } catch (error) {
        if ((error as any)?.status === 404) {
          return c.json({
            success: false,
            error: 'Minifig not found',
          }, 404);
        }
        
        return c.json({
          success: false,
          error: 'Server error',
        }, 500);
      }
    }
  );

  // Add OpenAPI documentation
  openApiApp.doc('/docs', {
    openapi: '3.0.0',
    info: {
      title: 'Bricks Deal API',
      version: '1.0.0',
      description: 'API for Bricks Deal application',
    },
    servers: [
      {
        url: 'http://localhost:8787',
        description: 'Local development server',
      },
      {
        url: 'https://api.bricksdeal.com',
        description: 'Production server',
      },
    ],
  });

  // Add Swagger UI
  openApiApp.get('/ui', swaggerUI({ url: '/api-docs/docs' }));

  return openApiApp;
} 