export function getApiUrl(): string {
  return import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
}

export function isDevBuild(): boolean {
  return import.meta.env.DEV
}
