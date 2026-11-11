import { useQuery } from '@tanstack/react-query'
import { type ReactNode, useState } from 'react'
import { Link } from 'react-router'
import { analyticsApi } from '../api/endpoints'
import { CategoryBars } from '../components/charts/CategoryBars'
import { MonthlyChart } from '../components/charts/MonthlyChart'
import { ColorDot } from '../components/ui/ColorDot'
import { ErrorMessage, FormField, inputClass } from '../components/ui/FormField'
import type { AnalyticsMonth, CategoryChange, Period } from '../types/api'
import { formatDate, formatMonth, formatPLN, formatPercent, monthRange } from '../utils/format'

const ALL = 'all'
// Trend z ostatniego roku; lista okresów do wyboru z pełnej historii.
const TREND_MONTHS = 12
const HISTORY_MONTHS = 36

/** Domyślny okres: ostatni pełny miesiąc, a bez pełnych miesięcy: najnowszy. */
function defaultMonth(months: AnalyticsMonth[]): string | null {
  const complete = months.filter((m) => m.complete)
  return (complete.at(-1) ?? months.at(-1))?.month ?? null
}

export function DashboardPage() {
  const history = useQuery({
    queryKey: ['analytics', 'monthly', HISTORY_MONTHS],
    queryFn: () => analyticsApi.monthly(HISTORY_MONTHS),
  })
  const [selected, setSelected] = useState<string | null>(null)
  const months = history.data ?? []
  const choice = selected ?? defaultMonth(months) ?? ALL
  const period: Period = choice === ALL ? {} : monthRange(choice)
  const enabled = history.isSuccess

  const summary = useQuery({
    queryKey: ['analytics', 'summary', period],
    queryFn: () => analyticsApi.summary(period),
    enabled,
  })
  const categories = useQuery({
    queryKey: ['analytics', 'by-category', period],
    queryFn: () => analyticsApi.byCategory(period),
    enabled,
  })
  const changes = useQuery({
    queryKey: ['analytics', 'changes', choice],
    queryFn: () => analyticsApi.changes(choice === ALL ? undefined : choice),
    enabled,
  })
  const top = useQuery({
    queryKey: ['analytics', 'top', period],
    queryFn: () => analyticsApi.top(period),
    enabled,
  })

  const error = [history, summary, categories, changes, top].find((q) => q.error)?.error
  const s = summary.data

  if (history.isSuccess && months.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-xl font-semibold text-slate-900">Pulpit</h1>
        <p className="text-sm text-slate-600">
          Nie ma jeszcze transakcji.{' '}
          <Link to="/import" className="font-medium text-emerald-700 underline">
            Zaimportuj wyciąg
          </Link>{' '}
          albo dodaj transakcję ręcznie, a tu pojawi się podsumowanie.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-xl font-semibold text-slate-900">Pulpit</h1>
        <div className="w-64">
          <FormField label="Okres">
            <select
              value={choice}
              onChange={(e) => setSelected(e.target.value)}
              className={inputClass}
            >
              {[...months].reverse().map((m) => (
                <option key={m.month} value={m.month}>
                  {formatMonth(m.month)}
                  {m.complete ? '' : ' (niepełny)'}
                </option>
              ))}
              <option value={ALL}>Cały okres</option>
            </select>
          </FormField>
        </div>
      </div>

      <ErrorMessage message={error ? error.message : null} />

      {s && (
        <section aria-label="Podsumowanie okresu" className="flex flex-col gap-2">
          <p className="text-sm text-slate-500">
            {formatDate(s.date_from)} – {formatDate(s.date_to)} · transakcji: {s.transactions}
            {choice !== ALL && !months.find((m) => m.month === choice)?.complete && (
              <> · miesiąc niepełny, sumy są niższe niż za cały miesiąc</>
            )}
          </p>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
            <Tile label="Przychody" value={formatPLN(s.income)} />
            <Tile label="Wydatki" value={formatPLN(s.expenses)} />
            <Tile label="Saldo" value={formatPLN(s.balance)} />
            <Tile
              label="Stopa oszczędności"
              value={s.savings_rate === null ? '—' : formatPercent(s.savings_rate)}
              hint="część przychodów, która nie została wydana"
            />
            <Tile
              label="Na własne konta"
              value={formatPLN(s.own_transfers_net)}
              hint="przelewy własne netto, np. Smart Saver; nie są wydatkiem"
            />
            <Tile label="Wydatki dziennie" value={formatPLN(s.avg_daily_expense)} hint="średnio" />
          </div>
          {s.uncategorized > 0 && (
            <p className="text-sm text-amber-800">
              {s.uncategorized} transakcji bez kategorii liczymy jako „Bez kategorii”.{' '}
              <Link to="/transactions" className="font-medium underline">
                Przypisz kategorie
              </Link>
            </p>
          )}
          {s.other_currency > 0 && (
            <p className="text-sm text-slate-500">
              Pominięto {s.other_currency} transakcji w innej walucie niż PLN.
            </p>
          )}
        </section>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Wydatki według kategorii">
          {categories.data && (
            <CategoryBars items={categories.data.expenses} label="Wydatki według kategorii" />
          )}
          {categories.data && categories.data.income.length > 0 && (
            <div className="mt-4 border-t border-slate-100 pt-3">
              <h3 className="mb-2 text-sm font-medium text-slate-700">Wpływy</h3>
              <ul className="flex flex-col gap-1 text-sm">
                {categories.data.income.map((c) => (
                  <li key={`${c.category_id}-${c.name}`} className="flex justify-between gap-2">
                    <span className="flex items-center gap-2 text-slate-700">
                      <ColorDot color={c.color} />
                      {c.name}
                    </span>
                    <span className="tabular-nums text-slate-900">{formatPLN(c.amount)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>

        <Card title="Przychody i wydatki miesięcznie">
          {history.data && <MonthlyChart months={history.data.slice(-TREND_MONTHS)} />}
        </Card>
      </div>

      {changes.data && changes.data.month && (
        <Card
          title={`Zmiany w kategoriach: ${formatMonth(changes.data.month)}${changes.data.complete ? '' : ' (niepełny)'}`}
        >
          <ChangesTable
            items={changes.data.items}
            previous={changes.data.previous_month}
            average={changes.data.average_months}
          />
        </Card>
      )}

      {top.data && (
        <div className="grid gap-6 xl:grid-cols-2">
          <Card title="Komu płacisz najwięcej">
            <ol className="flex flex-col gap-1 text-sm">
              {top.data.counterparties.map((c) => (
                <li key={c.name} className="flex justify-between gap-3">
                  <span className="truncate text-slate-700" title={c.name}>
                    {c.name} <span className="text-slate-400">× {c.count}</span>
                  </span>
                  <span className="whitespace-nowrap tabular-nums text-slate-900">
                    {formatPLN(c.amount)}
                  </span>
                </li>
              ))}
            </ol>
          </Card>
          <Card title="Największe wydatki">
            <ol className="flex flex-col gap-1 text-sm">
              {top.data.largest.map((e, i) => (
                <li key={i} className="flex justify-between gap-3">
                  <span className="min-w-0 truncate text-slate-700" title={e.description}>
                    <span className="text-slate-500">{formatDate(e.date)}</span>{' '}
                    {e.counterparty ?? e.description}{' '}
                    <span className="text-slate-400">· {e.category}</span>
                  </span>
                  <span className="whitespace-nowrap tabular-nums text-slate-900">
                    {formatPLN(e.amount)}
                  </span>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      )}
    </div>
  )
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section
      aria-label={title}
      className="flex flex-col gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200"
    >
      <h2 className="text-base font-semibold text-slate-900">{title}</h2>
      {children}
    </section>
  )
}

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl bg-white p-3 shadow-sm ring-1 ring-slate-200">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-lg font-semibold text-slate-900">{value}</p>
      {hint && <p className="text-xs text-slate-400">{hint}</p>}
    </div>
  )
}

/** Zmiana wydatków: wzrost czerwony ze strzałką w górę, spadek zielony ze strzałką w dół. */
function Change({ value }: { value: number | null }) {
  if (value === null) return <span className="text-slate-400">—</span>
  if (value === 0) return <span className="text-slate-600">0%</span>
  const up = value > 0
  return (
    <span className={up ? 'text-red-700' : 'text-emerald-700'}>
      <span aria-hidden="true">{up ? '▲' : '▼'} </span>
      <span className="sr-only">{up ? 'wzrost' : 'spadek'} </span>
      {formatPercent(Math.abs(value), 0)}
    </span>
  )
}

function ChangesTable({
  items,
  previous,
  average,
}: {
  items: CategoryChange[]
  previous: string | null
  average: string[]
}) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">Brak wydatków w tym miesiącu.</p>
  }
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-slate-500">
        {previous
          ? `Poprzedni miesiąc: ${formatMonth(previous)}. `
          : 'Brak pełnego poprzedniego miesiąca. '}
        {average.length > 0
          ? `Średnia z: ${average.map((m) => formatMonth(m, true)).join(', ')}.`
          : 'Brak pełnych miesięcy do średniej.'}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-slate-500">
            <tr>
              <th className="py-1 pr-3 font-medium">Kategoria</th>
              <th className="py-1 pr-3 text-right font-medium">W miesiącu</th>
              <th className="py-1 pr-3 text-right font-medium">Poprzedni</th>
              <th className="py-1 pr-3 text-right font-medium">Zmiana</th>
              <th className="py-1 pr-3 text-right font-medium">Średnia</th>
              <th className="py-1 text-right font-medium">Wobec średniej</th>
            </tr>
          </thead>
          <tbody className="tabular-nums text-slate-800">
            {items.map((c) => (
              <tr key={`${c.category_id}-${c.name}`} className="border-t border-slate-100">
                <td className="py-1 pr-3">
                  <span className="flex items-center gap-2">
                    <ColorDot color={c.color} />
                    {c.name}
                  </span>
                </td>
                <td className="py-1 pr-3 text-right">{formatPLN(c.current)}</td>
                <td className="py-1 pr-3 text-right">
                  {c.previous === null ? '—' : formatPLN(c.previous)}
                </td>
                <td className="py-1 pr-3 text-right">
                  <Change value={c.change_previous} />
                </td>
                <td className="py-1 pr-3 text-right">
                  {c.average === null ? '—' : formatPLN(c.average)}
                </td>
                <td className="py-1 text-right">
                  <Change value={c.change_average} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
