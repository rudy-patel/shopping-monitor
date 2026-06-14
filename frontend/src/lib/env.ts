export function getApiUrl(): string {
  return import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
}

export function isDevBuild(): boolean {
  return import.meta.env.DEV
}

export function isProductionBuild(): boolean {
  return import.meta.env.PROD || import.meta.env.VITE_APP_ENV === 'production'
}
