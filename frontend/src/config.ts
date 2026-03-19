/**
 * Centralized frontend configuration — reads from Vite env vars with defaults.
 *
 * In production, VITE_API_BASE_URL must be set in the root .env before building.
 * The fallback uses the current page's protocol + hostname to avoid accidental
 * plaintext HTTP in production deployments.
 */
const fallback =
  typeof window !== 'undefined' &&
  window.location.hostname !== 'localhost' &&
  window.location.hostname !== '127.0.0.1'
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : 'http://localhost:8000';

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL || fallback;
