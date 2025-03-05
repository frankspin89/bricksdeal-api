/**
 * LEGO Database API
 * This worker provides API endpoints to access the LEGO database.
 */

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      const path = url.pathname;
      
      // Enable CORS
      const corsHeaders = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      };
      
      // Handle OPTIONS request for CORS
      if (request.method === 'OPTIONS') {
        return new Response(null, {
          headers: corsHeaders,
        });
      }
      
      // Only allow GET requests
      if (request.method !== 'GET') {
        return new Response('Method not allowed', { status: 405 });
      }
      
      // API endpoints
      if (path === '/api/sets') {
        return await handleGetSets(request, env, corsHeaders);
      } else if (path.startsWith('/api/sets/')) {
        const setId = path.split('/').pop();
        return await handleGetSetById(setId, env, corsHeaders);
      } else if (path === '/api/themes') {
        return await handleGetThemes(env, corsHeaders);
      } else if (path === '/api/prices') {
        return await handleGetPrices(request, env, corsHeaders);
      } else if (path === '/api/search') {
        return await handleSearch(request, env, corsHeaders);
      } else if (path === '/') {
        return new Response('LEGO Database API', {
          headers: {
            'Content-Type': 'text/plain',
            ...corsHeaders,
          },
        });
      }
      
      // Not found
      return new Response('Not found', { status: 404, headers: corsHeaders });
    } catch (error) {
      return new Response(`Error: ${error.message}`, { status: 500 });
    }
  },
};

/**
 * Handle GET /api/sets
 * Returns a list of LEGO sets with pagination
 */
async function handleGetSets(request, env, corsHeaders) {
  const url = new URL(request.url);
  const page = parseInt(url.searchParams.get('page') || '1');
  const limit = parseInt(url.searchParams.get('limit') || '50');
  const theme = url.searchParams.get('theme');
  const year = url.searchParams.get('year');
  
  // Build the query
  let query = 'SELECT * FROM lego_sets';
  const params = [];
  
  // Add filters
  const filters = [];
  if (theme) {
    filters.push('theme LIKE ?');
    params.push(`%${theme}%`);
  }
  if (year) {
    filters.push('year_released = ?');
    params.push(year);
  }
  
  if (filters.length > 0) {
    query += ' WHERE ' + filters.join(' AND ');
  }
  
  // Add pagination
  query += ' ORDER BY year_released DESC, name LIMIT ? OFFSET ?';
  params.push(limit);
  params.push((page - 1) * limit);
  
  // Execute the query
  const { results } = await env.DB.prepare(query).bind(...params).all();
  
  // Get total count for pagination
  const countQuery = 'SELECT COUNT(*) as count FROM lego_sets';
  const { results: countResults } = await env.DB.prepare(countQuery).all();
  const totalCount = countResults[0].count;
  
  // Return the results
  return new Response(JSON.stringify({
    page,
    limit,
    total: totalCount,
    total_pages: Math.ceil(totalCount / limit),
    data: results,
  }), {
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders,
    },
  });
}

/**
 * Handle GET /api/sets/:id
 * Returns details for a specific LEGO set
 */
async function handleGetSetById(setId, env, corsHeaders) {
  // Get the set details
  const { results: setResults } = await env.DB.prepare(
    'SELECT * FROM lego_sets WHERE id = ?'
  ).bind(setId).all();
  
  if (setResults.length === 0) {
    return new Response('Set not found', { status: 404, headers: corsHeaders });
  }
  
  const set = setResults[0];
  
  // Get minifigures
  const { results: minifigures } = await env.DB.prepare(
    'SELECT * FROM minifigures WHERE set_id = ?'
  ).bind(setId).all();
  
  // Get images
  const { results: images } = await env.DB.prepare(
    'SELECT * FROM images WHERE set_id = ?'
  ).bind(setId).all();
  
  // Get price history
  const { results: prices } = await env.DB.prepare(
    'SELECT * FROM prices WHERE set_id = ? ORDER BY date DESC'
  ).bind(setId).all();
  
  // Get metadata
  const { results: metadata } = await env.DB.prepare(
    'SELECT * FROM metadata WHERE set_id = ?'
  ).bind(setId).all();
  
  // Format metadata as key-value pairs
  const metadataObj = {};
  for (const item of metadata) {
    metadataObj[item.key] = item.value;
  }
  
  // Return the combined data
  return new Response(JSON.stringify({
    ...set,
    minifigures,
    images,
    price_history: prices,
    metadata: metadataObj,
  }), {
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders,
    },
  });
}

/**
 * Handle GET /api/themes
 * Returns a list of all themes
 */
async function handleGetThemes(env, corsHeaders) {
  const { results } = await env.DB.prepare(
    'SELECT DISTINCT theme FROM lego_sets WHERE theme IS NOT NULL ORDER BY theme'
  ).all();
  
  return new Response(JSON.stringify(results), {
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders,
    },
  });
}

/**
 * Handle GET /api/prices
 * Returns price history for sets with recent changes
 */
async function handleGetPrices(request, env, corsHeaders) {
  const url = new URL(request.url);
  const days = parseInt(url.searchParams.get('days') || '30');
  
  // Get sets with price changes in the last X days
  const { results } = await env.DB.prepare(`
    SELECT p1.set_id, ls.name, p1.price as current_price, p1.currency, p1.date as current_date,
           p2.price as previous_price, p2.date as previous_date,
           (p1.price - p2.price) as price_change,
           ((p1.price - p2.price) / p2.price * 100) as price_change_percent
    FROM prices p1
    JOIN lego_sets ls ON p1.set_id = ls.id
    JOIN (
      SELECT set_id, MAX(date) as max_date
      FROM prices
      GROUP BY set_id
    ) latest ON p1.set_id = latest.set_id AND p1.date = latest.max_date
    JOIN prices p2 ON p1.set_id = p2.set_id
    JOIN (
      SELECT set_id, MAX(date) as max_date
      FROM prices
      WHERE date < (
        SELECT MAX(date) FROM prices p3 WHERE p3.set_id = set_id
      )
      GROUP BY set_id
    ) previous ON p2.set_id = previous.set_id AND p2.date = previous.max_date
    WHERE julianday('now') - julianday(p1.date) <= ?
    AND p1.price != p2.price
    ORDER BY price_change_percent DESC
  `).bind(days).all();
  
  return new Response(JSON.stringify(results), {
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders,
    },
  });
}

/**
 * Handle GET /api/search
 * Searches for LEGO sets by name, theme, or set number
 */
async function handleSearch(request, env, corsHeaders) {
  const url = new URL(request.url);
  const query = url.searchParams.get('q');
  
  if (!query) {
    return new Response(JSON.stringify({ error: 'Query parameter "q" is required' }), {
      status: 400,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders,
      },
    });
  }
  
  // Search for sets
  const { results } = await env.DB.prepare(`
    SELECT * FROM lego_sets
    WHERE id LIKE ? OR name LIKE ? OR theme LIKE ?
    ORDER BY year_released DESC, name
    LIMIT 50
  `).bind(`%${query}%`, `%${query}%`, `%${query}%`).all();
  
  return new Response(JSON.stringify(results), {
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders,
    },
  });
} 