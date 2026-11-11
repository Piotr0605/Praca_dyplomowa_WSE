import { useState } from 'react'
import type { AnalyticsMonth } from '../../types/api'
import { formatMonth, formatPLN, formatPercent } from '../../utils/format'

// Dwie serie: kolejne barwy palety kategorialnej (sprawdzonej pod kątem daltonizmu).
const INCOME = { label: 'Przychody', color: '#2a78d6' }
const EXPENSES = { label: 'Wydatki', color: '#eb6834' }

// Szerokość zbliżona do wyświetlanej, żeby napisy osi nie były pomniejszane.
const WIDTH = 540
const HEIGHT = 240
const MARGIN = { top: 12, right: 8, bottom: 32, left: 76 }
const BAR_MAX = 24
const BAR_GAP = 2
const RADIUS = 4

/** Okrągła górna granica osi i krok podziałki (1, 2 albo 5 × 10^n). */
function niceScale(max: number, ticks = 4): { top: number; step: number } {
  if (max <= 0) return { top: 1, step: 1 }
  const raw = max / ticks
  const power = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 5, 10].map((m) => m * power).find((s) => s >= raw) ?? 10 * power
  return { top: Math.ceil(max / step) * step, step }
}

function axisLabel(value: number): string {
  return value >= 10_000
    ? new Intl.NumberFormat('pl-PL', { notation: 'compact' }).format(value)
    : new Intl.NumberFormat('pl-PL').format(value)
}

/** Słupek z zaokrągloną górą i płaską podstawą na osi. */
function barPath(x: number, y: number, width: number, height: number): string {
  const r = Math.min(RADIUS, height, width / 2)
  const bottom = y + height
  return `M${x},${bottom} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${bottom} Z`
}

/** Przychody i wydatki w kolejnych miesiącach: słupki obok siebie, podpowiedź i tabela. */
export function MonthlyChart({ months }: { months: AnalyticsMonth[] }) {
  const [active, setActive] = useState<number | null>(null)
  if (months.length === 0) {
    return <p className="text-sm text-slate-500">Brak danych.</p>
  }

  const plotWidth = WIDTH - MARGIN.left - MARGIN.right
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom
  const values = months.flatMap((m) => [Number(m.income), Number(m.expenses)])
  const { top, step } = niceScale(Math.max(...values))
  const y = (v: number) => MARGIN.top + plotHeight - (v / top) * plotHeight
  const band = plotWidth / months.length
  const bar = Math.max(4, Math.min(BAR_MAX, (band - 16 - BAR_GAP) / 2))
  const ticks = Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step)
  const hasIncomplete = months.some((m) => !m.complete)
  const current = active === null ? null : months[active]

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-4 text-sm text-slate-700">
        {[INCOME, EXPENSES].map((s) => (
          <span key={s.label} className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="inline-block h-3 w-3 rounded-sm"
              style={{ backgroundColor: s.color }}
            />
            {s.label}
          </span>
        ))}
        {hasIncomplete && (
          <span className="text-slate-500">* niepełny miesiąc (słupki jaśniejsze)</span>
        )}
      </div>

      <div className="relative">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-auto w-full"
          role="img"
          aria-label="Przychody i wydatki w kolejnych miesiącach. Dokładne wartości w tabeli pod wykresem."
          onMouseLeave={() => setActive(null)}
        >
          {ticks.map((t) => (
            <g key={t}>
              <line
                x1={MARGIN.left}
                x2={WIDTH - MARGIN.right}
                y1={y(t)}
                y2={y(t)}
                stroke={t === 0 ? '#c3c2b7' : '#e1e0d9'}
                strokeWidth={1}
              />
              <text
                x={MARGIN.left - 8}
                y={y(t)}
                textAnchor="end"
                dominantBaseline="middle"
                className="fill-slate-500 text-[12px] tabular-nums"
              >
                {axisLabel(t)} zł
              </text>
            </g>
          ))}

          {months.map((m, i) => {
            const center = MARGIN.left + band * i + band / 2
            const opacity = m.complete ? 1 : 0.45
            return (
              <g key={m.month}>
                {[
                  { value: Number(m.income), color: INCOME.color, x: center - BAR_GAP / 2 - bar },
                  { value: Number(m.expenses), color: EXPENSES.color, x: center + BAR_GAP / 2 },
                ].map(
                  (b) =>
                    b.value > 0 && (
                      <path
                        key={b.color}
                        d={barPath(b.x, y(b.value), bar, y(0) - y(b.value))}
                        fill={b.color}
                        opacity={opacity}
                      />
                    ),
                )}
                <text
                  x={center}
                  y={HEIGHT - MARGIN.bottom + 18}
                  textAnchor="middle"
                  className="fill-slate-600 text-[12px]"
                >
                  {formatMonth(m.month, true)}
                  {m.complete ? '' : '*'}
                </text>
                {/* Obszar podpowiedzi większy niż słupki; dostępny też z klawiatury. */}
                <rect
                  x={MARGIN.left + band * i}
                  y={MARGIN.top}
                  width={band}
                  height={plotHeight}
                  fill="transparent"
                  tabIndex={0}
                  aria-label={`${formatMonth(m.month)}: przychody ${formatPLN(m.income)}, wydatki ${formatPLN(m.expenses)}`}
                  onMouseEnter={() => setActive(i)}
                  onFocus={() => setActive(i)}
                  onBlur={() => setActive(null)}
                  className="outline-none focus:stroke-slate-400"
                />
              </g>
            )
          })}
        </svg>

        {current && active !== null && (
          // Czytnik ekranu dostaje te same wartości z etykiety obszaru miesiąca.
          <div
            aria-hidden="true"
            className="pointer-events-none absolute top-2 z-10 w-56 rounded-lg bg-white p-3 text-sm shadow-md ring-1 ring-slate-200"
            style={{
              left: `${Math.min(
                Math.max(((MARGIN.left + band * active + band / 2) / WIDTH) * 100, 15),
                75,
              )}%`,
              transform: 'translateX(-50%)',
            }}
          >
            <p className="font-medium text-slate-900">
              {formatMonth(current.month)}
              {!current.complete && <span className="text-slate-500"> (niepełny)</span>}
            </p>
            <TooltipRow color={INCOME.color} label="Przychody" value={formatPLN(current.income)} />
            <TooltipRow
              color={EXPENSES.color}
              label="Wydatki"
              value={formatPLN(current.expenses)}
            />
            <p className="mt-1 flex justify-between border-t border-slate-100 pt-1 text-slate-700">
              <span>Saldo</span>
              <span className="tabular-nums">{formatPLN(current.balance)}</span>
            </p>
          </div>
        )}
      </div>

      <details className="text-sm">
        <summary className="cursor-pointer text-slate-600">Pokaż tabelę</summary>
        <table className="mt-2 w-full text-left">
          <thead className="text-xs text-slate-500">
            <tr>
              <th className="py-1 font-medium">Miesiąc</th>
              <th className="py-1 text-right font-medium">Przychody</th>
              <th className="py-1 text-right font-medium">Wydatki</th>
              <th className="py-1 text-right font-medium">Saldo</th>
              <th className="py-1 text-right font-medium">Stopa oszczędności</th>
            </tr>
          </thead>
          <tbody className="tabular-nums text-slate-800">
            {months.map((m) => (
              <tr key={m.month} className="border-t border-slate-100">
                <td className="py-1">
                  {formatMonth(m.month)}
                  {!m.complete && <span className="text-slate-500"> (niepełny)</span>}
                </td>
                <td className="py-1 text-right">{formatPLN(m.income)}</td>
                <td className="py-1 text-right">{formatPLN(m.expenses)}</td>
                <td className="py-1 text-right">{formatPLN(m.balance)}</td>
                <td className="py-1 text-right">
                  {m.savings_rate === null ? '—' : formatPercent(m.savings_rate)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}

function TooltipRow({ color, label, value }: { color: string; label: string; value: string }) {
  return (
    <p className="mt-1 flex items-center justify-between gap-2 text-slate-700">
      <span className="flex items-center gap-2">
        <span
          aria-hidden="true"
          className="inline-block h-2.5 w-2.5 rounded-sm"
          style={{ backgroundColor: color }}
        />
        {label}
      </span>
      <span className="tabular-nums text-slate-900">{value}</span>
    </p>
  )
}
