const ADMIN_KEY_KEY = 'lexai_admin_key';

export function getAdminKey(): string | null {
  return localStorage.getItem(ADMIN_KEY_KEY);
}

export function setAdminKey(key: string): void {
  localStorage.setItem(ADMIN_KEY_KEY, key);
}

export function clearAdminKey(): void {
  localStorage.removeItem(ADMIN_KEY_KEY);
}

export function isAdminAuthenticated(): boolean {
  const key = getAdminKey();
  return key !== null && key.trim().length > 0;
}
