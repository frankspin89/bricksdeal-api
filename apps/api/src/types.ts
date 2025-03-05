import type { D1Database, R2Bucket } from '@cloudflare/workers-types';

// Define custom environment
export interface AppVariables {
  user?: {
    userId: string;
    username: string;
    role: string;
  };
  [key: string]: any;
}

// Define the environment bindings
export interface Bindings {
  DB: D1Database;
  IMAGES: R2Bucket;
  JWT_SECRET: string;
  ADMIN_USERNAME: string;
  ADMIN_PASSWORD: string;
  CLOUDFLARE_ACCOUNT_ID: string;
  CLOUDFLARE_ACCESS_KEY_ID: string;
  CLOUDFLARE_SECRET_ACCESS_KEY: string;
  CLOUDFLARE_DOMAIN: string;
  CLOUDFLARE_R2_BUCKET: string;
  CLOUDFLARE_DATABASE_ID: string;
  OXYLABS_USERNAME: string;
  OXYLABS_PASSWORD: string;
  OXYLABS_ENDPOINT: string;
  OXYLABS_PORTS: string;
  DEEPSEEK_API_KEY: string;
  ENVIRONMENT?: string;
  [key: string]: any;
}

export type AppEnv = {
  Variables: AppVariables;
  Bindings: Bindings;
}; 