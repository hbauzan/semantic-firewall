/** Centralized frontend configuration — reads from Vite env vars with defaults. */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
