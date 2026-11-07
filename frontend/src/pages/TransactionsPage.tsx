import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { categoriesApi, transactionsApi } from '../api/endpoints'
import { TransactionForm } from '../components/transactions/TransactionForm'
import {
  ErrorMessage,
  FormField,
  inputClass,
  primaryButton,
  secondaryButton,
} from '../components/ui/FormField'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import type { Transaction, TransactionInput } from '../types/api'
import { KIND_LABELS, formatAmount, formatDate } from '../utils/format'

const PAGE_SIZE = 20

export function TransactionsPage() {
  const queryClient = useQueryClient()
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [adding, setAdding] = useState(false)
  const [editing, setEditing] = useState<Transaction | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const q = useDebouncedValue(search.trim())

  const filters = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    category_id: category && category !== 'none' ? Number(category) : undefined,
    uncategorized: category === 'none' ? true : undefined,
    q: q || undefined,
    page,
    page_size: PAGE_SIZE,
  }
  const categories = useQuery({ queryKey: ['categories'], queryFn: categoriesApi.list })
  const transactions = useQuery({
    queryKey: ['transactions', filters],
    queryFn: () => transactionsApi.list(filters),
    placeholderData: keepPreviousData,
  })
  const categoryName = new Map((categories.data ?? []).map((c) => [c.id, c.name]))
  const totalPages = Math.max(1, Math.ceil((transactions.data?.total ?? 0) / PAGE_SIZE))

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['transactions'] })
  const create = useMutation({ mutationFn: transactionsApi.create, onSuccess: refresh })
  const update = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<TransactionInput> }) =>
      transactionsApi.update(id, data),
    onSuccess: refresh,
  })
  const remove = useMutation({ mutationFn: transactionsApi.remove, onSuccess: refresh })

  function changeFilter(apply: () => void) {
    apply()
    setPage(1)
  }

  async function handleEdit(data: TransactionInput) {
    if (!editing) return
    // W transakcji z importu wysyłamy tylko pola, które API pozwala zmienić.
    const payload =
      editing.source === 'manual'
        ? data
        : { category_id: data.category_id, kind: data.kind, description: data.description }
    await update.mutateAsync({ id: editing.id, data: payload })
    setEditing(null)
  }

  async function handleDelete(transaction: Transaction) {
    if (!window.confirm(`Usunąć transakcję „${transaction.description}”?`)) return
    setActionError(null)
    try {
      await remove.mutateAsync(transaction.id)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Nie udało się usunąć')
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Transakcje</h1>
        {!adding && !editing && (
          <button type="button" onClick={() => setAdding(true)} className={primaryButton}>
            Dodaj transakcję
          </button>
        )}
      </div>

      {adding && (
        <TransactionForm
          categories={categories.data ?? []}
          onSubmit={async (data) => {
            await create.mutateAsync(data)
            setAdding(false)
          }}
          onCancel={() => setAdding(false)}
        />
      )}
      {editing && (
        <TransactionForm
          key={editing.id}
          categories={categories.data ?? []}
          initial={editing}
          onSubmit={handleEdit}
          onCancel={() => setEditing(null)}
        />
      )}

      <section aria-label="Filtry" className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <FormField label="Od">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => changeFilter(() => setDateFrom(e.target.value))}
            className={inputClass}
          />
        </FormField>
        <FormField label="Do">
          <input
            type="date"
            value={dateTo}
            onChange={(e) => changeFilter(() => setDateTo(e.target.value))}
            className={inputClass}
          />
        </FormField>
        <FormField label="Kategoria">
          <select
            value={category}
            onChange={(e) => changeFilter(() => setCategory(e.target.value))}
            className={inputClass}
          >
            <option value="">Wszystkie</option>
            <option value="none">Bez kategorii</option>
            {(categories.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Szukaj">
          <input
            type="search"
            value={search}
            onChange={(e) => changeFilter(() => setSearch(e.target.value))}
            placeholder="Opis lub kontrahent"
            className={inputClass}
          />
        </FormField>
      </section>

      <ErrorMessage
        message={actionError ?? (transactions.error ? transactions.error.message : null)}
      />

      <div className="overflow-x-auto rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-slate-600">
            <tr>
              <th scope="col" className="px-4 py-3 font-medium">
                Data
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Opis
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Kategoria
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Rodzaj
              </th>
              <th scope="col" className="px-4 py-3 text-right font-medium">
                Kwota
              </th>
              <th scope="col" className="px-4 py-3">
                <span className="sr-only">Akcje</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {transactions.data?.items.map((t) => (
              <tr key={t.id} className="border-b border-slate-100 last:border-0">
                <td className="whitespace-nowrap px-4 py-3 text-slate-700">{formatDate(t.date)}</td>
                <td className="px-4 py-3">
                  <span className="text-slate-900">{t.description}</span>
                  {t.counterparty && (
                    <span className="block text-xs text-slate-500">{t.counterparty}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-700">
                  {t.category_id ? (
                    categoryName.get(t.category_id)
                  ) : (
                    <span className="text-slate-400">brak</span>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-700">{KIND_LABELS[t.kind]}</td>
                <td
                  className={`whitespace-nowrap px-4 py-3 text-right font-medium tabular-nums ${t.amount.startsWith('-') ? 'text-slate-900' : 'text-emerald-700'}`}
                >
                  {formatAmount(t.amount, t.currency)}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-right">
                  <button
                    type="button"
                    onClick={() => {
                      setAdding(false)
                      setEditing(t)
                    }}
                    className="mr-3 text-emerald-700 hover:underline"
                  >
                    Edytuj<span className="sr-only"> {t.description}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(t)}
                    className="text-red-700 hover:underline"
                  >
                    Usuń<span className="sr-only"> {t.description}</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {transactions.data && transactions.data.items.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-slate-500">
            Brak transakcji. Dodaj pierwszą albo zmień filtry.
          </p>
        )}
        {transactions.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-500">Wczytywanie…</p>
        )}
      </div>

      <nav aria-label="Strony" className="flex items-center justify-between text-sm text-slate-600">
        <span>Wyników: {transactions.data?.total ?? 0}</span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            className={secondaryButton}
          >
            Poprzednia
          </button>
          <span>
            Strona {page} z {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
            className={secondaryButton}
          >
            Następna
          </button>
        </div>
      </nav>
    </div>
  )
}
