import { useEffect, useState } from 'react'
import { getHealth } from '../api/client'

const REFRESH_INTERVAL_MS = 10_000

/** Stan usługi; `null` oznacza, że pierwsze sprawdzenie jeszcze trwa. */
type ServiceState = { api: boolean; database: boolean } | null

function StatusRow({ label, ok }: { label: string; ok: boolean | null }) {
  const color = ok === null ? 'bg-slate-300' : ok ? 'bg-emerald-500' : 'bg-red-500'
  const text = ok === null ? 'Sprawdzanie…' : ok ? 'OK' : 'Błąd'

  return (
    <div className="flex items-center justify-between gap-8 py-2">
      <span className="font-medium text-slate-700">{label}</span>
      <span className="flex items-center gap-2 text-slate-900">
        <span aria-hidden="true" className={`size-3 rounded-full ${color}`} />
        {text}
      </span>
    </div>
  )
}

/** Pokazuje na żywo, czy frontend łączy się z API i czy API łączy się z bazą. */
export function HealthStatus() {
  const [state, setState] = useState<ServiceState>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function check() {
      try {
        const health = await getHealth(controller.signal)
        setState({ api: true, database: health.database === 'ok' })
      } catch {
        if (controller.signal.aborted) return
        // API nie odpowiada, więc stanu bazy nie znamy i traktujemy go jako błąd.
        setState({ api: false, database: false })
      }
    }

    void check()
    const timer = setInterval(() => void check(), REFRESH_INTERVAL_MS)

    return () => {
      clearInterval(timer)
      controller.abort()
    }
  }, [])

  return (
    <section aria-live="polite" className="divide-y divide-slate-100">
      <StatusRow label="API" ok={state && state.api} />
      <StatusRow label="Baza" ok={state && state.database} />
    </section>
  )
}
