// API response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  pagination?: Pagination;
  meta?: {
    changes?: number;
    last_row_id?: number;
  };
}

export interface Pagination {
  limit: number;
  offset: number;
  total: number;
}

// LEGO set types
export interface LegoSet {
  set_num: string;
  name: string;
  year: number;
  theme_id: number;
  num_parts?: number;
  img_url?: string;
  price?: number;
  price_updated_at?: string;
  theme_name?: string;
}

export interface LegoSetWithTheme extends LegoSet {
  theme_name: string;
}

// LEGO minifigure types
export interface LegoMinifig {
  fig_num: string;
  name: string;
  num_parts?: number;
  img_url?: string;
}

// LEGO theme types
export interface LegoTheme {
  id: number;
  name: string;
  parent_id?: number | null;
}

// API endpoints
export const API_ENDPOINTS = {
  SETS: '/api/sets',
  MINIFIGS: '/api/minifigs',
  THEMES: '/api/themes',
} as const;

// Utility types
export type SortDirection = 'asc' | 'desc';

export interface SortOptions {
  field: string;
  direction: SortDirection;
}

export interface FilterOptions {
  theme_id?: number;
  year?: number;
  search?: string;
} 