import { Hono } from 'hono';
import { z } from 'zod';
import { zValidator } from '@hono/zod-validator';

// Define the environment bindings
type Bindings = {
  DB: D1Database;
  IMAGES: R2Bucket;
};

// Create the router
const setsRouter = new Hono<{ Bindings: Bindings }>();

// Define the Set schema
const SetSchema = z.object({
  set_num: z.string(),
  name: z.string(),
  year: z.number(),
  theme_id: z.number(),
  num_parts: z.number().optional(),
  img_url: z.string().optional(),
  price: z.number().optional(),
  price_updated_at: z.string().optional(),
});

type Set = z.infer<typeof SetSchema>;

// GET /api/sets
setsRouter.get('/', async (c) => {
  try {
    const { limit = '50', offset = '0', theme_id, year, search } = c.req.query();
    
    let query = 'SELECT * FROM sets';
    const params: any[] = [];
    
    // Build the WHERE clause
    const conditions: string[] = [];
    
    if (theme_id) {
      conditions.push('theme_id = ?');
      params.push(theme_id);
    }
    
    if (year) {
      conditions.push('year = ?');
      params.push(year);
    }
    
    if (search) {
      conditions.push('name LIKE ?');
      params.push(`%${search}%`);
    }
    
    if (conditions.length > 0) {
      query += ' WHERE ' + conditions.join(' AND ');
    }
    
    // Add pagination
    query += ' ORDER BY year DESC, name ASC LIMIT ? OFFSET ?';
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
    console.error('Error fetching sets:', error);
    return c.json({
      success: false,
      error: 'Failed to fetch sets',
    }, 500);
  }
});

// GET /api/sets/:set_num
setsRouter.get('/:set_num', async (c) => {
  try {
    const set_num = c.req.param('set_num');
    
    const result = await c.env.DB.prepare(
      'SELECT s.*, t.name as theme_name FROM sets s JOIN themes t ON s.theme_id = t.id WHERE s.set_num = ?'
    ).bind(set_num).first();
    
    if (!result) {
      return c.json({
        success: false,
        error: 'Set not found',
      }, 404);
    }
    
    return c.json({
      success: true,
      data: result,
    });
  } catch (error) {
    console.error('Error fetching set:', error);
    return c.json({
      success: false,
      error: 'Failed to fetch set',
    }, 500);
  }
});

// POST /api/sets (for admin use)
setsRouter.post(
  '/',
  zValidator('json', SetSchema),
  async (c) => {
    try {
      const set = c.req.valid('json');
      
      const result = await c.env.DB.prepare(
        'INSERT INTO sets (set_num, name, year, theme_id, num_parts, img_url, price, price_updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
      ).bind(
        set.set_num,
        set.name,
        set.year,
        set.theme_id,
        set.num_parts || null,
        set.img_url || null,
        set.price || null,
        set.price_updated_at || null
      ).run();
      
      return c.json({
        success: true,
        data: set,
        meta: {
          changes: result.meta.changes,
          last_row_id: result.meta.last_row_id,
        },
      }, 201);
    } catch (error) {
      console.error('Error creating set:', error);
      return c.json({
        success: false,
        error: 'Failed to create set',
      }, 500);
    }
  }
);

// PUT /api/sets/:set_num (for admin use)
setsRouter.put(
  '/:set_num',
  zValidator('json', SetSchema.partial()),
  async (c) => {
    try {
      const set_num = c.req.param('set_num');
      const updates = c.req.valid('json');
      
      // Build the SET clause
      const setClause: string[] = [];
      const params: any[] = [];
      
      Object.entries(updates).forEach(([key, value]) => {
        if (key !== 'set_num') { // Don't update the primary key
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
      params.push(set_num);
      
      const result = await c.env.DB.prepare(
        `UPDATE sets SET ${setClause.join(', ')} WHERE set_num = ?`
      ).bind(...params).run();
      
      if (result.meta.changes === 0) {
        return c.json({
          success: false,
          error: 'Set not found',
        }, 404);
      }
      
      return c.json({
        success: true,
        meta: {
          changes: result.meta.changes,
        },
      });
    } catch (error) {
      console.error('Error updating set:', error);
      return c.json({
        success: false,
        error: 'Failed to update set',
      }, 500);
    }
  }
);

// DELETE /api/sets/:set_num (for admin use)
setsRouter.delete('/:set_num', async (c) => {
  try {
    const set_num = c.req.param('set_num');
    
    const result = await c.env.DB.prepare(
      'DELETE FROM sets WHERE set_num = ?'
    ).bind(set_num).run();
    
    if (result.meta.changes === 0) {
      return c.json({
        success: false,
        error: 'Set not found',
      }, 404);
    }
    
    return c.json({
      success: true,
      meta: {
        changes: result.meta.changes,
      },
    });
  } catch (error) {
    console.error('Error deleting set:', error);
    return c.json({
      success: false,
      error: 'Failed to delete set',
    }, 500);
  }
});

export { setsRouter }; 