/** Odpowiedź GET /api/health. */
export type HealthResponse = {
  status: 'ok' | 'degraded'
  database: 'ok' | 'error'
}
