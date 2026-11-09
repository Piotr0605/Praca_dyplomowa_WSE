import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { categorizationApi } from '../../api/endpoints'
import { secondaryButton } from '../ui/FormField'

type Props = {
  onShowUncategorized: () => void
}

/** Skąd pochodzą kategorie transakcji i przycisk przypisania kategorii transakcjom bez kategorii. */
export function CategorizationBar({ onShowUncategorized }: Props) {
  const queryClient = useQueryClient()
  const [message, setMessage] = useState<string | null>(null)
  const stats = useQuery({ queryKey: ['categorization-stats'], queryFn: categorizationApi.stats })
  const apply = useMutation({
    mutationFn: () => categorizationApi.apply(),
    onSuccess: ({ categorized }) => {
      setMessage(
        categorized === 0
          ? 'Żadna reguła nie pasuje do transakcji bez kategorii.'
          : `Przypisano kategorie: ${categorized}.`,
      )
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['categorization-stats'] })
    },
    onError: (err) => setMessage(err.message),
  })

  const s = stats.data
  if (!s || s.total === 0) return null
  const automatic = s.system_rule + s.user_rule
  const percent = Math.round((100 * automatic) / s.total)

  return (
    <section
      aria-label="Kategoryzacja"
      className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white px-4 py-3 text-sm shadow-sm ring-1 ring-slate-200"
    >
      <p className="text-slate-700">
        Kategorie automatyczne: <strong>{percent}%</strong> ({s.system_rule} ze słownika,{' '}
        {s.user_rule} z Twoich reguł) · ręcznie: {s.manual} · bez kategorii:{' '}
        <strong>{s.uncategorized}</strong>
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {message && (
          <span role="status" className="text-slate-600">
            {message}
          </span>
        )}
        {s.uncategorized > 0 && (
          <>
            <button type="button" onClick={onShowUncategorized} className={secondaryButton}>
              Do przypisania ({s.uncategorized})
            </button>
            <button
              type="button"
              disabled={apply.isPending}
              onClick={() => {
                setMessage(null)
                apply.mutate()
              }}
              className={secondaryButton}
            >
              {apply.isPending ? 'Przypisywanie…' : 'Przypisz kategorie automatycznie'}
            </button>
          </>
        )}
      </div>
    </section>
  )
}
