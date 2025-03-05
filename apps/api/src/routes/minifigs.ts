import { Hono } from 'hono';
import { z } from 'zod';
import { zValidator } from '@hono/zod-validator';

// Define the environment bindings
type Bindings = {
  DB: D1Database;
  IMAGES: R2Bucket;
};

// Create the router
const minifigsRouter = new Hono<{ Bindings: Bindings }>();

// Define the Minifig schema
const MinifigSchema = z.object({
  fig_num: z.string(),
  name: z.string(),
  num_parts: z.number().optional(),
  img_url: z.string().optional(),
});

type Minifig = z.infer<typeof MinifigSchema>;

// GET /api/minifigs
minifigsRouter.get('/', async (c) => {
  try {
    const { limit = '50', offset = '0', search } = c.req.query();
    
    let query = 'SELECT * FROM minifigs';
    const params: any[] = [];
    
    // Build the WHERE clause
    if (search) {
      query += ' WHERE name LIKE ?';
      params.push(`%${search}%`);
    }
    
    // Add pagination
    query += ' ORDER BY name ASC LIMIT ? OFFSET ?';
    params.push(parseInt(limit), parseInt(offset));
    
    const result = await c.env.DB.prepare(query).bind(...params).all();
    
    return c.json({
      success: true,
      data: result.results,
      pagination: {
        limit: parseInt(limit),
        offset: parseInt(offset),
        total: result.results.length, // This should ideally be a count query
      },
    });
  } catch (error) {
    console.error('Error fetching minifigs:', error);
    return c.json({
      success: false,
      error: 'Failed to fetch minifigs',
    }, 500);
  }
});

// GET /api/minifigs/:fig_num
minifigsRouter.get('/:fig_num', async (c) => {
  try {
    const fig_num = c.req.param('fig_num');
    
    const result = await c.env.DB.prepare(
      'SELECT * FROM minifigs WHERE fig_num = ?'
    ).bind(fig_num).first();
    
    if (!result) {
      return c.json({
        success: false,
        error: 'Minifig not found',
      }, 404);
    }
    
    return c.json({
      success: true,
      data: result,
    });
  } catch (error) {
    console.error('Error fetching minifig:', error);
    return c.json({
      success: false,
      error: 'Failed to fetch minifig',
    }, 500);
  }
});

// POST /api/minifigs (for admin use)
minifigsRouter.post(
  '/',
  zValidator('json', MinifigSchema),
  async (c) => {
    try {
      const minifig = c.req.valid('json');
      
      const result = await c.env.DB.prepare(
        'INSERT INTO minifigs (fig_num, name, num_parts, img_url) VALUES (?, ?, ?, ?)'
      ).bind(
        minifig.fig_num,
        minifig.name,
        minifig.num_parts || null,
        minifig.img_url || null
      ).run();
      
      return c.json({
        success: true,
        data: minifig,
        meta: {
          changes: result.meta.changes,
          last_row_id: result.meta.last_row_id,
        },
      }, 201);
    } catch (error) {
      console.error('Error creating minifig:', error);
      return c.json({
        success: false,
        error: 'Failed to create minifig',
      }, 500);
    }
  }
);

// PUT /api/minifigs/:fig_num (for admin use)
minifigsRouter.put(
  '/:fig_num',
  zValidator('json', MinifigSchema.partial()),
  async (c) => {
    try {
      const fig_num = c.req.param('fig_num');
      const updates = c.req.valid('json');
      
      // Build the SET clause
      const setClause: string[] = [];
      const params: any[] = [];
      
      Object.entries(updates).forEach(([key, value]) => {
        if (key !== 'fig_num') { // Don't update the primary key
          setClause.push(`${key} = ?`);
          params.push(value);
        }
      });
      
      if (setClause.length === 0) {
        return c.json({
          success: false,
          error: 'No valid fields to update',
        }, 400);
      }
      
      // Add the WHERE clause parameter
      params.push(fig_num);
      
      const result = await c.env.DB.prepare(
        `UPDATE minifigs SET ${setClause.join(', ')} WHERE fig_num = ?`
      ).bind(...params).run();
      
      if (result.meta.changes === 0) {
        return c.json({
          success: false,
          error: 'Minifig not found',
        }, 404);
      }
      
      return c.json({
        success: true,
        meta: {
          changes: result.meta.changes,
        },
      });
    } catch (error) {
      console.error('Error updating minifig:', error);
      return c.json({
        success: false,
        error: 'Failed to update minifig',
      }, 500);
    }
  }
);

// DELETE /api/minifigs/:fig_num (for admin use)
minifigsRouter.delete('/:fig_num', async (c) => {
  try {
    const fig_num = c.req.param('fig_num');
    
    const result = await c.env.DB.prepare(
      'DELETE FROM minifigs WHERE fig_num = ?'
    ).bind(fig_num).run();
    
    if (result.meta.changes === 0) {
      return c.json({
        success: false,
        error: 'Minifig not found',
      }, 404);
    }
    
    return c.json({
      success: true,
      meta: {
        changes: result.meta.changes,
      },
    });
  } catch (error) {
    console.error('Error deleting minifig:', error);
    return c.json({
      success: false,
      error: 'Failed to delete minifig',
    }, 500);
  }
});

export { minifigsRouter }; 