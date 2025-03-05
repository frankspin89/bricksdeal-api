/**
 * Environment variable validation script
 * 
 * This script validates that all required environment variables are set
 * and logs warnings for any missing variables.
 */

import config, { initEnv } from './config';

// Helper function to check if a variable exists in the environment
const hasEnv = (key: string): boolean => {
  try {
    // This will throw an error if the variable is required and not set
    const value = config.CLOUDFLARE.ACCOUNT_ID;
    return true;
  } catch (e) {
    return false;
  }
};

// Helper function to get a variable value safely
const getEnv = (key: string): string | undefined => {
  try {
    switch (key) {
      case 'JWT_SECRET':
        return String(config.AUTH.JWT_SECRET);
      case 'ADMIN_USERNAME':
        return config.AUTH.ADMIN_USERNAME;
      case 'ADMIN_PASSWORD':
        return config.AUTH.ADMIN_PASSWORD;
      case 'CLOUDFLARE_ACCOUNT_ID':
        return config.CLOUDFLARE.ACCOUNT_ID;
      case 'CLOUDFLARE_ACCESS_KEY_ID':
        return config.CLOUDFLARE.ACCESS_KEY_ID;
      case 'CLOUDFLARE_SECRET_ACCESS_KEY':
        return config.CLOUDFLARE.SECRET_ACCESS_KEY;
      case 'CLOUDFLARE_R2_BUCKET':
        return config.CLOUDFLARE.R2_BUCKET;
      case 'CLOUDFLARE_DOMAIN':
        return config.CLOUDFLARE.DOMAIN;
      case 'CLOUDFLARE_DATABASE_ID':
        return config.CLOUDFLARE.DATABASE_ID;
      case 'OXYLABS_USERNAME':
        return config.OXYLABS.USERNAME;
      case 'OXYLABS_PASSWORD':
        return config.OXYLABS.PASSWORD;
      case 'OXYLABS_ENDPOINT':
        return config.OXYLABS.ENDPOINT;
      case 'DEEPSEEK_API_KEY':
        return config.DEEPSEEK.API_KEY;
      default:
        return undefined;
    }
  } catch (e) {
    return undefined;
  }
};

export function validateEnvironment(): void {
  console.log('Validating environment variables...');
  
  // Determine if we're in development mode
  const isDevelopment = !config.IS_PRODUCTION;
  
  const missingVars: string[] = [];
  const warnings: string[] = [];
  
  // Check authentication variables
  const jwtSecret = getEnv('JWT_SECRET');
  if (!jwtSecret || jwtSecret === 'your-secret-key-change-in-production') {
    warnings.push('JWT_SECRET is using the default value. This is insecure for production environments.');
  }
  
  const adminUsername = getEnv('ADMIN_USERNAME');
  if (!adminUsername || adminUsername === 'admin') {
    warnings.push('ADMIN_USERNAME is using the default value. This is insecure for production environments.');
  }
  
  const adminPassword = getEnv('ADMIN_PASSWORD');
  if (!adminPassword || adminPassword === 'password' || adminPassword === 'secure-password-for-admin') {
    warnings.push('ADMIN_PASSWORD is using the default value. This is insecure for production environments.');
  }
  
  // In development mode, we don't need to check for missing variables
  if (!isDevelopment) {
    // Check Cloudflare variables
    if (!getEnv('CLOUDFLARE_ACCOUNT_ID')) missingVars.push('CLOUDFLARE_ACCOUNT_ID');
    if (!getEnv('CLOUDFLARE_ACCESS_KEY_ID')) missingVars.push('CLOUDFLARE_ACCESS_KEY_ID');
    if (!getEnv('CLOUDFLARE_SECRET_ACCESS_KEY')) missingVars.push('CLOUDFLARE_SECRET_ACCESS_KEY');
    if (!getEnv('CLOUDFLARE_R2_BUCKET')) missingVars.push('CLOUDFLARE_R2_BUCKET');
    if (!getEnv('CLOUDFLARE_DOMAIN')) missingVars.push('CLOUDFLARE_DOMAIN');
    if (!getEnv('CLOUDFLARE_DATABASE_ID')) missingVars.push('CLOUDFLARE_DATABASE_ID');
    
    // Check Oxylabs variables
    if (!getEnv('OXYLABS_USERNAME')) missingVars.push('OXYLABS_USERNAME');
    if (!getEnv('OXYLABS_PASSWORD')) missingVars.push('OXYLABS_PASSWORD');
    if (!getEnv('OXYLABS_ENDPOINT')) missingVars.push('OXYLABS_ENDPOINT');
    
    // Check DeepSeek variables
    if (!getEnv('DEEPSEEK_API_KEY')) missingVars.push('DEEPSEEK_API_KEY');
  }
  
  // Check if Cloudflare database ID is using the placeholder value
  const databaseId = getEnv('CLOUDFLARE_DATABASE_ID');
  if (databaseId === 'your-cloudflare-database-id') {
    warnings.push('CLOUDFLARE_DATABASE_ID is using a placeholder value. Please update it with your actual database ID.');
  }
  
  // Log results
  if (missingVars.length > 0) {
    console.warn('⚠️ Missing environment variables:');
    missingVars.forEach(variable => console.warn(`  - ${variable}`));
  }
  
  if (warnings.length > 0) {
    console.warn('⚠️ Environment variable warnings:');
    warnings.forEach(warning => console.warn(`  - ${warning}`));
  }
  
  if (missingVars.length === 0 && warnings.length === 0) {
    console.log('✅ All environment variables are properly configured.');
  }
  
  console.log('Environment validation complete.');
}

// Export the validation function
export default validateEnvironment; 