import type { HealthResponse } from '../types/api'

const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * Sprawdza stan API i bazy.
 *
 * 503 to prawidłowa odpowiedź: API działa, ale nie ma połączenia z bazą, dlatego treść jest
 * odczytywana także wtedy. Brak odpowiedzi (API wyłączone, błąd CORS) oraz każdy inny kod
 * kończą się wyjątkiem.
 */
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/api/health`, { signal })
  if (!response.ok && response.status !== 503) {
    throw new Error(`Nieoczekiwany kod odpowiedzi: ${response.status}`)
  }
  return (await response.json()) as HealthResponse
}
