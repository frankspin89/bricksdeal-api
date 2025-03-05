import { Hono } from 'hono';
import { getCookie, setCookie } from 'hono/cookie';
import { HTTPException } from 'hono/http-exception';
import jwt from 'jsonwebtoken';
import { Context, Env } from 'hono';
import { AUTH_CONFIG } from '../config';

// User payload type
interface UserPayload {
  userId: string;
  username: string;
  role: string;
}

// Define custom environment
interface AppVariables {
  user?: UserPayload;
  [key: string]: any;
}

type AppEnv = Env & {
  Variables: AppVariables;
};

// Authentication middleware
export const authMiddleware = async (c: Context<AppEnv>, next: () => Promise<void>) => {
  try {
    // Get token from cookie
    const token = getCookie(c, AUTH_CONFIG.COOKIE_NAME);
    
    if (!token) {
      throw new HTTPException(401, { message: 'Unauthorized' });
    }
    
    // Verify token
    try {
      const payload = jwt.verify(token, AUTH_CONFIG.JWT_SECRET) as UserPayload;
      
      if (!payload || payload.role !== 'admin') {
        throw new HTTPException(403, { message: 'Forbidden' });
      }
      
      // Add user to context
      c.set('user', payload);
      
      await next();
    } catch (error) {
      throw new HTTPException(401, { message: 'Invalid token' });
    }
  } catch (error) {
    throw new HTTPException(401, { message: 'Unauthorized' });
  }
};

// Login handler
export const loginHandler = async (c: Context) => {
  try {
    const { username, password } = await c.req.json();
    
    // Validate credentials (in production, check against database)
    if (username !== AUTH_CONFIG.ADMIN_USERNAME || password !== AUTH_CONFIG.ADMIN_PASSWORD) {
      throw new HTTPException(401, { message: 'Invalid credentials' });
    }
    
    // Generate token
    const payload: UserPayload = {
      userId: '1',
      username,
      role: 'admin'
    };
    
    const token = jwt.sign(
      payload, 
      AUTH_CONFIG.JWT_SECRET as string, 
      { expiresIn: AUTH_CONFIG.JWT_EXPIRATION } as jwt.SignOptions
    );
    
    // Set cookie
    setCookie(c, AUTH_CONFIG.COOKIE_NAME, token, AUTH_CONFIG.COOKIE_OPTIONS);
    
    return c.json({ success: true, message: 'Login successful' });
  } catch (error) {
    return c.json({ success: false, message: 'Login failed' }, 401);
  }
};

// Logout handler
export const logoutHandler = (c: Context) => {
  setCookie(c, AUTH_CONFIG.COOKIE_NAME, '', {
    ...AUTH_CONFIG.COOKIE_OPTIONS,
    maxAge: 0
  });
  
  return c.json({ success: true, message: 'Logout successful' });
};

// Create auth routes
export const createAuthRoutes = (app: Hono<AppEnv>) => {
  app.post('/auth/login', loginHandler);
  app.post('/auth/logout', logoutHandler);
  
  // Test route to verify authentication
  app.get('/auth/me', authMiddleware, (c) => {
    const user = c.get('user');
    return c.json({ user });
  });
  
  return app;
}; 