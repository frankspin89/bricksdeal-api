import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('Environment Validation', () => {
  // Store original environment variables and console methods
  const originalEnv = { ...process.env };
  const originalConsoleLog = console.log;
  const originalConsoleWarn = console.warn;
  
  beforeEach(() => {
    // Clear the module cache to ensure fresh imports
    vi.resetModules();
    
    // Mock console methods to prevent test output pollution
    console.log = vi.fn();
    console.warn = vi.fn();
    
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
    // Restore original environment variables and console methods
    process.env = { ...originalEnv };
    console.log = originalConsoleLog;
    console.warn = originalConsoleWarn;
  });
  
  it('should validate all environment variables successfully', async () => {
    // Import the validation module
    const { validateEnvironment } = await import('../src/validateEnv');
    
    // Run the validation
    validateEnvironment();
    
    // Expect success message to be logged
    expect(console.log).toHaveBeenCalledWith('Validating environment variables...');
    expect(console.log).toHaveBeenCalledWith('✅ All environment variables are properly configured.');
    expect(console.log).toHaveBeenCalledWith('Environment validation complete.');
    
    // Expect no warnings
    expect(console.warn).not.toHaveBeenCalled();
  });
  
  it('should warn about default values', async () => {
    // Set environment variables to default values
    process.env.JWT_SECRET = 'your-secret-key-change-in-production';
    process.env.ADMIN_USERNAME = 'admin';
    process.env.ADMIN_PASSWORD = 'password';
    
    // Import the validation module
    const { validateEnvironment } = await import('../src/validateEnv');
    
    // Run the validation
    validateEnvironment();
    
    // Expect warnings to be logged
    expect(console.warn).toHaveBeenCalledWith('⚠️ Environment variable warnings:');
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining('JWT_SECRET is using the default value'));
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining('ADMIN_USERNAME is using the default value'));
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining('ADMIN_PASSWORD is using the default value'));
  });
  
  it('should warn about missing environment variables', async () => {
    // Remove some required environment variables
    delete process.env.CLOUDFLARE_ACCOUNT_ID;
    delete process.env.OXYLABS_USERNAME;
    delete process.env.DEEPSEEK_API_KEY;
    delete process.env.CLOUDFLARE_DATABASE_ID;
    
    // Import the validation module
    const { validateEnvironment } = await import('../src/validateEnv');
    
    // Run the validation
    validateEnvironment();
    
    // Expect warnings to be logged
    expect(console.warn).toHaveBeenCalledWith('⚠️ Missing environment variables:');
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining('CLOUDFLARE_ACCOUNT_ID'));
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining('OXYLABS_USERNAME'));
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining('DEEPSEEK_API_KEY'));
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining('CLOUDFLARE_DATABASE_ID'));
  });
  
  it('should warn about placeholder database ID', async () => {
    // Set database ID to placeholder value
    process.env.CLOUDFLARE_DATABASE_ID = 'your-cloudflare-database-id';
    
    // Import the validation module
    const { validateEnvironment } = await import('../src/validateEnv');
    
    // Run the validation
    validateEnvironment();
    
    // Expect warnings to be logged
    expect(console.warn).toHaveBeenCalledWith('⚠️ Environment variable warnings:');
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining('CLOUDFLARE_DATABASE_ID is using a placeholder value'));
  });
}); 