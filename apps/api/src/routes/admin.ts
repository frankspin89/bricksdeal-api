import { Hono } from 'hono';
import { authMiddleware } from '../middleware/auth';
import { Context, Env } from 'hono';

// Define custom environment
interface AppVariables {
  user?: {
    userId: string;
    username: string;
    role: string;
  };
  [key: string]: any;
}

type AppEnv = Env & {
  Variables: AppVariables;
};

// Create admin routes
export const createAdminRoutes = (app: Hono<AppEnv>) => {
  const admin = new Hono<AppEnv>();
  
  // Apply auth middleware to all admin routes
  admin.use('*', authMiddleware);
  
  // Admin dashboard data
  admin.get('/', (c) => {
    return c.json({
      success: true,
      message: 'Admin dashboard data',
      stats: {
        totalSets: 12500,
        totalMinifigs: 8700,
        totalThemes: 150,
        recentUpdates: 42
      }
    });
  });
  
  // Update set data
  admin.put('/sets/:id', async (c) => {
    const id = c.req.param('id');
    const data = await c.req.json();
    
    // In a real implementation, you would update the database
    return c.json({
      success: true,
      message: `Set ${id} updated successfully`,
      data
    });
  });
  
  // Update minifig data
  admin.put('/minifigs/:id', async (c) => {
    const id = c.req.param('id');
    const data = await c.req.json();
    
    // In a real implementation, you would update the database
    return c.json({
      success: true,
      message: `Minifig ${id} updated successfully`,
      data
    });
  });
  
  // Trigger data refresh
  admin.post('/refresh', async (c) => {
    // In a real implementation, you would trigger a background job
    return c.json({
      success: true,
      message: 'Data refresh initiated',
      jobId: 'job-' + Date.now()
    });
  });
  
  // Mount admin routes
  app.route('/admin', admin);
  
  return app;
}; 