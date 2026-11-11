import type { CategoryAmount } from '../../types/api'
import { formatPLN, formatPercent } from '../../utils/format'
import { ColorDot } from '../ui/ColorDot'

/** Jeden kolor dla wszystkich słupków: porównujemy wielkości, a nazwa kategorii jest obok słupka. */
const BAR_COLOR = '#2a78d6'

type Props = {
  items: CategoryAmount[]
  /** Nazwa listy dla czytników ekranu, np. „Wydatki według kategorii”. */
  label: string
}

/** Poziome słupki posortowane od największej kwoty, z kwotą i udziałem przy końcu słupka. */
export function CategoryBars({ items, label }: Props) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">Brak danych w wybranym okresie.</p>
  }
  const max = Math.max(...items.map((i) => Number(i.amount)))

  return (
    <ul aria-label={label} className="flex flex-col gap-2">
      {items.map((item) => {
        const width = max > 0 ? (100 * Number(item.amount)) / max : 0
        return (
          <li
            key={`${item.category_id}-${item.name}`}
            className="grid grid-cols-[minmax(7rem,11rem)_1fr] items-center gap-3 text-sm"
          >
            <span className="flex min-w-0 items-center gap-2 text-slate-700">
              <ColorDot color={item.color} />
              <span className="truncate" title={item.name}>
                {item.name}
              </span>
            </span>
            <span className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className="h-4 rounded-r"
                style={{
                  width: `max(${width * 0.7}%, 2px)`,
                  backgroundColor: BAR_COLOR,
                }}
              />
              <span className="whitespace-nowrap tabular-nums text-slate-900">
                {formatPLN(item.amount)}
                <span className="ml-1 text-slate-500">({formatPercent(item.share)})</span>
              </span>
            </span>
          </li>
        )
      })}
    </ul>
  )
}
