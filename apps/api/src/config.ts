/**
 * Configuration file for the API
 * Centralizes environment variable handling and validation
 */

import jwt from 'jsonwebtoken';

// Global environment variables object
// This will be populated by the worker's env object
let envVars: Record<string, string> = {};

// Function to initialize environment variables from the worker's env object
export function initEnv(env: Record<string, string>): void {
  envVars = env;
}

// Helper function to check required environment variables
const requireEnv = (key: string, fallback?: string): string => {
  // First check if the variable is in the envVars object (from worker env)
  const value = envVars[key];
  
  if (!value) {
    // Fallback to process.env for local development
    const processValue = typeof process !== 'undefined' && process.env ? process.env[key] : undefined;
    
    if (processValue) {
      return processValue;
    }
    
    if (fallback !== undefined) {
      console.warn(`Environment variable ${key} is not set. Using fallback value for development only.`);
      return fallback;
    }
    throw new Error(`Required environment variable ${key} is not set.`);
  }
  return value;
};

// Authentication configuration
export const AUTH_CONFIG = {
  get JWT_SECRET() {
    return requireEnv('JWT_SECRET', 'your-secret-key-change-in-production') as jwt.Secret;
  },
  JWT_EXPIRATION: '24h',
  COOKIE_NAME: 'bricks-deal-auth',
  COOKIE_OPTIONS: {
    httpOnly: true,
    path: '/',
    secure: envVars.ENVIRONMENT === 'production',
    sameSite: 'Lax' as const,
  },
  get ADMIN_USERNAME() {
    return requireEnv('ADMIN_USERNAME', 'admin');
  },
  get ADMIN_PASSWORD() {
    return requireEnv('ADMIN_PASSWORD', 'password');
  },
};

// Cloudflare R2 configuration
export const CLOUDFLARE_CONFIG = {
  get ACCOUNT_ID() {
    return requireEnv('CLOUDFLARE_ACCOUNT_ID');
  },
  get ACCESS_KEY_ID() {
    return requireEnv('CLOUDFLARE_ACCESS_KEY_ID');
  },
  get SECRET_ACCESS_KEY() {
    return requireEnv('CLOUDFLARE_SECRET_ACCESS_KEY');
  },
  get R2_BUCKET() {
    return requireEnv('CLOUDFLARE_R2_BUCKET', 'lego-images');
  },
  get DOMAIN() {
    return requireEnv('CLOUDFLARE_DOMAIN', 'images.bricksdeal.com');
  },
  get DATABASE_ID() {
    return requireEnv('CLOUDFLARE_DATABASE_ID');
  },
  get R2_ENDPOINT() {
    return `https://${this.ACCOUNT_ID}.r2.cloudflarestorage.com`;
  }
};

// Oxylabs proxy configuration
export const OXYLABS_CONFIG = {
  get USERNAME() {
    return requireEnv('OXYLABS_USERNAME');
  },
  get PASSWORD() {
    return requireEnv('OXYLABS_PASSWORD');
  },
  get ENDPOINT() {
    return requireEnv('OXYLABS_ENDPOINT', 'dc.oxylabs.io');
  },
  get PORTS(): number[] {
    try {
      const portsStr = requireEnv('OXYLABS_PORTS', '8001,8002,8003,8004,8005');
      const ports = portsStr.split(',')
        .map(port => port.trim())
        .filter(port => /^\d+$/.test(port))
        .map(port => parseInt(port, 10));
      
      if (ports.length === 0) {
        return [8001, 8002, 8003, 8004, 8005]; // Default ports
      }
      
      return ports;
    } catch (e) {
      console.warn(`Error parsing OXYLABS_PORTS: ${e}. Using default ports.`);
      return [8001, 8002, 8003, 8004, 8005];
    }
  }
};

// DeepSeek API configuration
export const DEEPSEEK_CONFIG = {
  get API_KEY() {
    return requireEnv('DEEPSEEK_API_KEY');
  },
  API_URL: 'https://api.deepseek.com/v1/chat/completions',
};

// Export all configurations
export default {
  AUTH: AUTH_CONFIG,
  CLOUDFLARE: CLOUDFLARE_CONFIG,
  OXYLABS: OXYLABS_CONFIG,
  DEEPSEEK: DEEPSEEK_CONFIG,
  get IS_PRODUCTION() {
    return envVars.ENVIRONMENT === 'production';
  },
}; 