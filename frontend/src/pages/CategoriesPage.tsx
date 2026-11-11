import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { categoriesApi, rulesApi } from '../api/endpoints'
import {
  ErrorMessage,
  FormField,
  inputClass,
  primaryButton,
  secondaryButton,
} from '../components/ui/FormField'
import { ColorDot } from '../components/ui/ColorDot'
import type { Category } from '../types/api'

const DEFAULT_COLOR = '#64748b'

/** Kategorie systemowe (tylko do odczytu), własne kategorie i reguły zapamiętane z poprawek. */
export function CategoriesPage() {
  const queryClient = useQueryClient()
  const categories = useQuery({ queryKey: ['categories'], queryFn: categoriesApi.list })
  const rules = useQuery({ queryKey: ['rules'], queryFn: rulesApi.list })
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [color, setColor] = useState(DEFAULT_COLOR)
  const [isIncome, setIsIncome] = useState(false)
  const [editing, setEditing] = useState<Category | null>(null)

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['categories'] })
    queryClient.invalidateQueries({ queryKey: ['rules'] })
    queryClient.invalidateQueries({ queryKey: ['transactions'] })
    queryClient.invalidateQueries({ queryKey: ['categorization-stats'] })
  }
  const onError = (err: Error) => setError(err.message)
  const create = useMutation({ mutationFn: categoriesApi.create, onSuccess: refresh, onError })
  const update = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name: string; color: string } }) =>
      categoriesApi.update(id, data),
    onSuccess: () => {
      setEditing(null)
      refresh()
    },
    onError,
  })
  const remove = useMutation({ mutationFn: categoriesApi.remove, onSuccess: refresh, onError })
  const removeRule = useMutation({ mutationFn: rulesApi.remove, onSuccess: refresh, onError })

  const system = (categories.data ?? []).filter((c) => c.is_system)
  const own = (categories.data ?? []).filter((c) => !c.is_system)

  function add(event: FormEvent) {
    event.preventDefault()
    setError(null)
    // mutate, a nie mutateAsync: błąd (np. zajęta nazwa) obsługuje onError, bez nieobsłużonego wyjątku.
    create.mutate(
      { name: name.trim(), color, is_income: isIncome },
      {
        onSuccess: () => {
          setName('')
          setColor(DEFAULT_COLOR)
          setIsIncome(false)
        },
      },
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-slate-900">Kategorie</h1>
      <ErrorMessage message={error} />

      <form
        onSubmit={add}
        aria-label="Nowa kategoria"
        className="grid gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 md:grid-cols-[1fr_auto_auto_auto] md:items-end"
      >
        <FormField label="Nazwa nowej kategorii">
          <input
            value={name}
            maxLength={100}
            onChange={(e) => setName(e.target.value)}
            placeholder="np. Zwierzęta"
            className={inputClass}
          />
        </FormField>
        <FormField label="Kolor">
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="h-10 w-16 rounded-md border border-slate-300"
          />
        </FormField>
        <label className="flex items-center gap-2 pb-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={isIncome}
            onChange={(e) => setIsIncome(e.target.checked)}
          />
          przychód
        </label>
        <button type="submit" disabled={!name.trim() || create.isPending} className={primaryButton}>
          Dodaj
        </button>
      </form>

      <section aria-label="Własne kategorie" className="flex flex-col gap-2">
        <h2 className="text-base font-semibold text-slate-900">Własne kategorie</h2>
        {own.length === 0 && (
          <p className="text-sm text-slate-500">Nie masz jeszcze własnych kategorii.</p>
        )}
        {own.length > 0 && (
          <ul className="divide-y divide-slate-100 rounded-xl bg-white text-sm shadow-sm ring-1 ring-slate-200">
            {own.map((c) =>
              editing?.id === c.id ? (
                <li key={c.id} className="flex flex-wrap items-end gap-3 px-4 py-2">
                  <FormField label="Nazwa">
                    <input
                      value={editing.name}
                      maxLength={100}
                      onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                      className={inputClass}
                    />
                  </FormField>
                  <FormField label="Kolor">
                    <input
                      type="color"
                      value={editing.color ?? DEFAULT_COLOR}
                      onChange={(e) => setEditing({ ...editing, color: e.target.value })}
                      className="h-10 w-16 rounded-md border border-slate-300"
                    />
                  </FormField>
                  <button
                    type="button"
                    disabled={!editing.name.trim() || update.isPending}
                    onClick={() => {
                      setError(null)
                      update.mutate({
                        id: c.id,
                        data: { name: editing.name.trim(), color: editing.color ?? DEFAULT_COLOR },
                      })
                    }}
                    className={primaryButton}
                  >
                    Zapisz
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditing(null)}
                    className={secondaryButton}
                  >
                    Anuluj
                  </button>
                </li>
              ) : (
                <li key={c.id} className="flex items-center justify-between gap-4 px-4 py-2">
                  <span className="flex items-center gap-2 text-slate-800">
                    <ColorDot color={c.color} />
                    {c.name}
                    {c.is_income && <span className="text-xs text-emerald-700">przychód</span>}
                  </span>
                  <span className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setEditing(c)}
                      className="text-emerald-700 hover:underline"
                    >
                      Edytuj<span className="sr-only"> {c.name}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (
                          window.confirm(
                            `Usunąć kategorię „${c.name}”? Transakcje zostaną bez kategorii, a reguły tej kategorii zostaną usunięte.`,
                          )
                        ) {
                          setError(null)
                          remove.mutate(c.id)
                        }
                      }}
                      className="text-red-700 hover:underline"
                    >
                      Usuń<span className="sr-only"> {c.name}</span>
                    </button>
                  </span>
                </li>
              ),
            )}
          </ul>
        )}
      </section>

      <section aria-label="Zapamiętane reguły" className="flex flex-col gap-2">
        <h2 className="text-base font-semibold text-slate-900">Zapamiętane reguły</h2>
        <p className="text-sm text-slate-500">
          Reguła powstaje, gdy zmienisz kategorię transakcji: kolejne transakcje od tego samego
          kontrahenta dostaną tę kategorię automatycznie. Usunięcie reguły nie zmienia kategorii już
          przypisanych.
        </p>
        {rules.data && rules.data.length === 0 && (
          <p className="text-sm text-slate-500">Nie ma jeszcze zapamiętanych reguł.</p>
        )}
        {rules.data && rules.data.length > 0 && (
          <ul className="divide-y divide-slate-100 rounded-xl bg-white text-sm shadow-sm ring-1 ring-slate-200">
            {rules.data.map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-4 px-4 py-2">
                <span className="text-slate-800">
                  {r.match_type === 'exact_counterparty' ? 'Kontrahent' : 'Tekst zawiera'} „
                  {r.pattern}” → <strong>{r.category_name}</strong>
                  <span className="ml-2 text-xs text-slate-500">transakcji: {r.transactions}</span>
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setError(null)
                    removeRule.mutate(r.id)
                  }}
                  className="text-red-700 hover:underline"
                >
                  Usuń<span className="sr-only"> regułę {r.pattern}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Kategorie systemowe" className="flex flex-col gap-2">
        <h2 className="text-base font-semibold text-slate-900">Kategorie systemowe</h2>
        <p className="text-sm text-slate-500">
          Wspólne dla wszystkich użytkowników, nie można ich zmienić. Słownik przypisuje do nich
          transakcje popularnych sklepów i usług.
        </p>
        <ul className="flex flex-wrap gap-2">
          {system.map((c) => (
            <li
              key={c.id}
              className="flex items-center gap-2 rounded-full bg-white px-3 py-1 text-sm text-slate-700 ring-1 ring-slate-200"
            >
              <ColorDot color={c.color} />
              {c.name}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
