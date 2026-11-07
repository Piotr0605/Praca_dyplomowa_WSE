import type { HealthResponse } from '../types/api'
import { tokenStore } from './token'

const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/** Błąd odpowiedzi API z kodem HTTP i komunikatem z pola `detail`. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

let onUnauthorized: () => void = () => {}

/** Reakcja na odrzucony token, np. po jego wygaśnięciu: ustawia ją kontekst logowania. */
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler
}

type Detail = string | { msg: string; loc?: (string | number)[] }[]

function messageFrom(detail: Detail | undefined, status: number): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => `${d.loc?.at(-1) ?? 'dane'}: ${d.msg}`).join('; ')
  }
  return `Błąd serwera (${status})`
}

type RequestOptions = {
  method?: string
  json?: unknown
  form?: Record<string, string>
  query?: Record<string, string | number | boolean | undefined>
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(`${API_URL}/api${path}`)
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== '') url.searchParams.set(key, String(value))
  }

  const headers: Record<string, string> = {}
  const token = tokenStore.get()
  if (token) headers.Authorization = `Bearer ${token}`
  let body: BodyInit | undefined
  if (options.json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.json)
  } else if (options.form) {
    body = new URLSearchParams(options.form)
  }

  const response = await fetch(url, { method: options.method ?? 'GET', headers, body })
  if (response.status === 401 && token) onUnauthorized()
  if (!response.ok) {
    const data = (await response.json().catch(() => ({}))) as { detail?: Detail }
    throw new ApiError(response.status, messageFrom(data.detail, response.status))
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

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
