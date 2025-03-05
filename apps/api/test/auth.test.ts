import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Hono } from 'hono';
import { authMiddleware, loginHandler, logoutHandler } from '../src/middleware/auth';
import jwt from 'jsonwebtoken';
import { AUTH_CONFIG } from '../src/config';

// Mock the next function
const mockNext = vi.fn();

// Create a mock context
const createMockContext = (cookies = {}, body = {}) => {
  return {
    req: {
      json: vi.fn().mockResolvedValue(body),
    },
    get: vi.fn(),
    set: vi.fn(),
    json: vi.fn().mockReturnThis(),
    status: vi.fn().mockReturnThis(),
    cookie: cookies,
    header: {},
    env: {},
  };
};

describe('Auth Middleware', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should reject requests without a token', async () => {
    const mockContext = createMockContext();
    
    // Mock getCookie to return null (no token)
    vi.mock('hono/cookie', () => ({
      getCookie: vi.fn().mockReturnValue(null),
      setCookie: vi.fn(),
    }));
    
    // Expect the middleware to throw an error
    await expect(authMiddleware(mockContext as any, mockNext)).rejects.toThrow('Unauthorized');
    expect(mockNext).not.toHaveBeenCalled();
  });

  it('should reject requests with an invalid token', async () => {
    const mockContext = createMockContext({ 'bricks-deal-auth': 'invalid-token' });
    
    // Mock getCookie to return an invalid token
    vi.mock('hono/cookie', () => ({
      getCookie: vi.fn().mockReturnValue('invalid-token'),
      setCookie: vi.fn(),
    }));
    
    // Mock jwt.verify to throw an error
    vi.mock('jsonwebtoken', () => ({
      verify: vi.fn().mockImplementation(() => {
        throw new Error('Invalid token');
      }),
      sign: vi.fn(),
    }));
    
    // Expect the middleware to throw an error
    await expect(authMiddleware(mockContext as any, mockNext)).rejects.toThrow('Unauthorized');
    expect(mockNext).not.toHaveBeenCalled();
  });

  it('should allow requests with a valid admin token', async () => {
    const mockContext = createMockContext({ 'bricks-deal-auth': 'valid-token' });
    
    // Mock getCookie to return a valid token
    vi.mock('hono/cookie', () => ({
      getCookie: vi.fn().mockReturnValue('valid-token'),
      setCookie: vi.fn(),
    }));
    
    // Mock jwt.verify to return a valid payload
    vi.mock('jsonwebtoken', () => ({
      verify: vi.fn().mockReturnValue({
        userId: '1',
        username: 'admin',
        role: 'admin',
      }),
      sign: vi.fn(),
    }));
    
    // Call the middleware
    await authMiddleware(mockContext as any, mockNext);
    
    // Expect the middleware to set the user in the context and call next
    expect(mockContext.set).toHaveBeenCalledWith('user', {
      userId: '1',
      username: 'admin',
      role: 'admin',
    });
    expect(mockNext).toHaveBeenCalled();
  });
});

describe('Login Handler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should reject login with invalid credentials', async () => {
    const mockContext = createMockContext({}, {
      username: 'wrong-user',
      password: 'wrong-password',
    });
    
    // Call the login handler
    const result = await loginHandler(mockContext as any);
    
    // Expect the handler to return an error response
    expect(mockContext.json).toHaveBeenCalledWith(
      { success: false, message: 'Login failed' },
      401
    );
  });

  it('should accept login with valid credentials', async () => {
    const mockContext = createMockContext({}, {
      username: AUTH_CONFIG.ADMIN_USERNAME,
      password: AUTH_CONFIG.ADMIN_PASSWORD,
    });
    
    // Mock jwt.sign to return a token
    vi.mock('jsonwebtoken', () => ({
      sign: vi.fn().mockReturnValue('valid-token'),
      verify: vi.fn(),
    }));
    
    // Mock setCookie
    const setCookieMock = vi.fn();
    vi.mock('hono/cookie', () => ({
      getCookie: vi.fn(),
      setCookie: setCookieMock,
    }));
    
    // Call the login handler
    const result = await loginHandler(mockContext as any);
    
    // Expect the handler to set a cookie and return a success response
    expect(setCookieMock).toHaveBeenCalled();
    expect(mockContext.json).toHaveBeenCalledWith(
      { success: true, message: 'Login successful' }
    );
  });
});

describe('Logout Handler', () => {
  it('should clear the auth cookie', () => {
    const mockContext = createMockContext();
    
    // Mock setCookie
    const setCookieMock = vi.fn();
    vi.mock('hono/cookie', () => ({
      getCookie: vi.fn(),
      setCookie: setCookieMock,
    }));
    
    // Call the logout handler
    const result = logoutHandler(mockContext as any);
    
    // Expect the handler to clear the cookie and return a success response
    expect(setCookieMock).toHaveBeenCalledWith(
      mockContext,
      AUTH_CONFIG.COOKIE_NAME,
      '',
      expect.objectContaining({ maxAge: 0 })
    );
    expect(mockContext.json).toHaveBeenCalledWith(
      { success: true, message: 'Logout successful' }
    );
  });
}); 