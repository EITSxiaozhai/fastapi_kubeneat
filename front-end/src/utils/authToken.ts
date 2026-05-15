export const AUTH_TOKEN_STORAGE_KEY = 'kubeneat.jwt';

export function getAuthToken() {
  if (typeof window === 'undefined') {
    return undefined;
  }
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || undefined;
}

export function saveAuthToken(token: string) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

export function clearAuthToken() {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}
