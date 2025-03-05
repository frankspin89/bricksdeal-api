import { Hono } from 'hono';
import { z } from 'zod';
import { zValidator } from '@hono/zod-validator';

// Define the environment bindings
type Bindings = {
  DB: D1Database;
  IMAGES: R2Bucket;
};

// Create the router
const themesRouter = new Hono<{ Bindings: Bindings }>();

// Define the Theme schema
const ThemeSchema = z.object({
  id: z.number(),
  name: z.string(),
  parent_id: z.number().optional().nullable(),
});

type Theme = z.infer<typeof ThemeSchema>;

// GET /api/themes
themesRouter.get('/', async (c) => {
  try {
    const { parent_id, search } = c.req.query();
    
    let query = 'SELECT * FROM themes';
    const params: any[] = [];
    
    // Build the WHERE clause
    const conditions: string[] = [];
    
    if (parent_id) {
      conditions.push('parent_id = ?');
      params.push(parent_id);
    }
    
    if (search) {
      conditions.push('name LIKE ?');
      params.push(`%${search}%`);
    }
    
    if (conditions.length > 0) {
      query += ' WHERE ' + conditions.join(' AND ');
    }
    
    // Add ordering
    query += ' ORDER BY name ASC';
    
    const result = await c.env.DB.prepare(query).bind(...params).all();
    
    return c.json({
      success: true,
      data: result.results,
    });
  } catch (error) {
    console.error('Error fetching themes:', error);
    return c.json({
      success: false,
      error: 'Failed to fetch themes',
    }, 500);
  }
});

// GET /api/themes/:id
themesRouter.get('/:id', async (c) => {
  try {
    const id = c.req.param('id');
    
    const result = await c.env.DB.prepare(
      'SELECT * FROM themes WHERE id = ?'
    ).bind(id).first();
    
    if (!result) {
      return c.json({
        success: false,
        error: 'Theme not found',
      }, 404);
    }
    
    return c.json({
      success: true,
      data: result,
    });
  } catch (error) {
    console.error('Error fetching theme:', error);
    return c.json({
      success: false,
      error: 'Failed to fetch theme',
    }, 500);
  }
});

// GET /api/themes/:id/sets
themesRouter.get('/:id/sets', async (c) => {
  try {
    const id = c.req.param('id');
    const { limit = '50', offset = '0' } = c.req.query();
    
    // First, check if the theme exists
    const themeExists = await c.env.DB.prepare(
      'SELECT id FROM themes WHERE id = ?'
    ).bind(id).first();
    
    if (!themeExists) {
      return c.json({
        success: false,
        error: 'Theme not found',
      }, 404);
    }
    
    // Get all sets for this theme
    const result = await c.env.DB.prepare(
      'SELECT * FROM sets WHERE theme_id = ? ORDER BY year DESC, name ASC LIMIT ? OFFSET ?'
    ).bind(id, parseInt(limit), parseInt(offset)).all();
    
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
    console.error('Error fetching sets for theme:', error);
    return c.json({
      success: false,
      error: 'Failed to fetch sets for theme',
    }, 500);
  }
});

// POST /api/themes (for admin use)
themesRouter.post(
  '/',
  zValidator('json', ThemeSchema),
  async (c) => {
    try {
      const theme = c.req.valid('json');
      
      const result = await c.env.DB.prepare(
        'INSERT INTO themes (id, name, parent_id) VALUES (?, ?, ?)'
      ).bind(
        theme.id,
        theme.name,
        theme.parent_id || null
      ).run();
      
      return c.json({
        success: true,
        data: theme,
        meta: {
          changes: result.meta.changes,
          last_row_id: result.meta.last_row_id,
        },
      }, 201);
    } catch (error) {
      console.error('Error creating theme:', error);
      return c.json({
        success: false,
        error: 'Failed to create theme',
      }, 500);
    }
  }
);

// PUT /api/themes/:id (for admin use)
themesRouter.put(
  '/:id',
  zValidator('json', ThemeSchema.partial()),
  async (c) => {
    try {
      const id = c.req.param('id');
      const updates = c.req.valid('json');
      
      // Build the SET clause
      const setClause: string[] = [];
      const params: any[] = [];
      
      Object.entries(updates).forEach(([key, value]) => {
        if (key !== 'id') { // Don't update the primary key
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
      params.push(id);
      
      const result = await c.env.DB.prepare(
        `UPDATE themes SET ${setClause.join(', ')} WHERE id = ?`
      ).bind(...params).run();
      
      if (result.meta.changes === 0) {
        return c.json({
          success: false,
          error: 'Theme not found',
        }, 404);
      }
      
      return c.json({
        success: true,
        meta: {
          changes: result.meta.changes,
        },
      });
    } catch (error) {
      console.error('Error updating theme:', error);
      return c.json({
        success: false,
        error: 'Failed to update theme',
      }, 500);
    }
  }
);

// DELETE /api/themes/:id (for admin use)
themesRouter.delete('/:id', async (c) => {
  try {
    const id = c.req.param('id');
    
    // Check if there are any sets using this theme
    const setsUsingTheme = await c.env.DB.prepare(
      'SELECT COUNT(*) as count FROM sets WHERE theme_id = ?'
    ).bind(id).first();
    
    if (setsUsingTheme && Number(setsUsingTheme.count) > 0) {
      return c.json({
        success: false,
        error: 'Cannot delete theme with associated sets',
      }, 400);
    }
    
    // Check if there are any child themes
    const childThemes = await c.env.DB.prepare(
      'SELECT COUNT(*) as count FROM themes WHERE parent_id = ?'
    ).bind(id).first();
    
    if (childThemes && Number(childThemes.count) > 0) {
      return c.json({
        success: false,
        error: 'Cannot delete theme with child themes',
      }, 400);
    }
    
    const result = await c.env.DB.prepare(
      'DELETE FROM themes WHERE id = ?'
    ).bind(id).run();
    
    if (result.meta.changes === 0) {
      return c.json({
        success: false,
        error: 'Theme not found',
      }, 404);
    }
    
    return c.json({
      success: true,
      meta: {
        changes: result.meta.changes,
      },
    });
  } catch (error) {
    console.error('Error deleting theme:', error);
    return c.json({
      success: false,
      error: 'Failed to delete theme',
    }, 500);
  }
});

export { themesRouter }; 