import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('Config Module', () => {
  // Store original environment variables
  const originalEnv = { ...process.env };
  
  beforeEach(() => {
    // Clear the module cache to ensure fresh imports
    vi.resetModules();
    
    // Set up test environment variables
    process.env.JWT_SECRET = 'test-jwt-secret';
    process.env.ADMIN_USERNAME = 'test-admin';
    process.env.ADMIN_PASSWORD = 'test-password';
    process.env.CLOUDFLARE_ACCOUNT_ID = 'test-account-id';
    process.env.CLOUDFLARE_ACCESS_KEY_ID = 'test-access-key';
    process.env.CLOUDFLARE_SECRET_ACCESS_KEY = 'test-secret-key';
    process.env.CLOUDFLARE_R2_BUCKET = 'test-bucket';
    process.env.CLOUDFLARE_DOMAIN = 'test.example.com';
    process.env.CLOUDFLARE_DATABASE_ID = 'test-database-id';
    process.env.OXYLABS_USERNAME = 'test-oxylabs-user';
    process.env.OXYLABS_PASSWORD = 'test-oxylabs-pass';
    process.env.OXYLABS_ENDPOINT = 'test.oxylabs.io';
    process.env.OXYLABS_PORTS = '1001,1002,1003';
    process.env.DEEPSEEK_API_KEY = 'test-deepseek-key';
  });
  
  afterEach(() => {
    // Restore original environment variables
    process.env = { ...originalEnv };
  });
  
  it('should load environment variables correctly', async () => {
    // Import the config module after setting up the environment
    const { AUTH_CONFIG, CLOUDFLARE_CONFIG, OXYLABS_CONFIG, DEEPSEEK_CONFIG } = await import('../src/config');
    
    // Test AUTH_CONFIG
    expect(AUTH_CONFIG.JWT_SECRET).toBe('test-jwt-secret');
    expect(AUTH_CONFIG.ADMIN_USERNAME).toBe('test-admin');
    expect(AUTH_CONFIG.ADMIN_PASSWORD).toBe('test-password');
    
    // Test CLOUDFLARE_CONFIG
    expect(CLOUDFLARE_CONFIG.ACCOUNT_ID).toBe('test-account-id');
    expect(CLOUDFLARE_CONFIG.ACCESS_KEY_ID).toBe('test-access-key');
    expect(CLOUDFLARE_CONFIG.SECRET_ACCESS_KEY).toBe('test-secret-key');
    expect(CLOUDFLARE_CONFIG.R2_BUCKET).toBe('test-bucket');
    expect(CLOUDFLARE_CONFIG.DOMAIN).toBe('test.example.com');
    expect(CLOUDFLARE_CONFIG.DATABASE_ID).toBe('test-database-id');
    expect(CLOUDFLARE_CONFIG.R2_ENDPOINT).toBe('https://test-account-id.r2.cloudflarestorage.com');
    
    // Test OXYLABS_CONFIG
    expect(OXYLABS_CONFIG.USERNAME).toBe('test-oxylabs-user');
    expect(OXYLABS_CONFIG.PASSWORD).toBe('test-oxylabs-pass');
    expect(OXYLABS_CONFIG.ENDPOINT).toBe('test.oxylabs.io');
    expect(OXYLABS_CONFIG.PORTS).toEqual([1001, 1002, 1003]);
    
    // Test DEEPSEEK_CONFIG
    expect(DEEPSEEK_CONFIG.API_KEY).toBe('test-deepseek-key');
  });
  
  it('should handle missing environment variables with fallbacks', async () => {
    // Remove some environment variables to test fallbacks
    delete process.env.JWT_SECRET;
    delete process.env.CLOUDFLARE_R2_BUCKET;
    delete process.env.CLOUDFLARE_DOMAIN;
    delete process.env.OXYLABS_ENDPOINT;
    
    // Mock console.warn to prevent test output pollution
    const consoleWarnMock = vi.spyOn(console, 'warn').mockImplementation(() => {});
    
    // Import the config module after modifying the environment
    const { AUTH_CONFIG, CLOUDFLARE_CONFIG, OXYLABS_CONFIG } = await import('../src/config');
    
    // Test fallbacks
    expect(AUTH_CONFIG.JWT_SECRET).toBe('your-secret-key-change-in-production');
    expect(CLOUDFLARE_CONFIG.R2_BUCKET).toBe('lego-images');
    expect(CLOUDFLARE_CONFIG.DOMAIN).toBe('images.bricksdeal.com');
    expect(OXYLABS_CONFIG.ENDPOINT).toBe('dc.oxylabs.io');
    
    // Verify console.warn was called for each missing variable
    expect(consoleWarnMock).toHaveBeenCalledTimes(4);
    
    // Restore console.warn
    consoleWarnMock.mockRestore();
  });
  
  it('should throw error for required environment variables with no fallback', async () => {
    // Remove a required environment variable
    delete process.env.CLOUDFLARE_ACCOUNT_ID;
    
    // Expect the import to throw an error
    await expect(import('../src/config')).rejects.toThrow('Required environment variable CLOUDFLARE_ACCOUNT_ID is not set.');
  });
}); 