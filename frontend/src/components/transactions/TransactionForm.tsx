import { type FormEvent, useState } from 'react'
import {
  type Category,
  TRANSACTION_KINDS,
  type Transaction,
  type TransactionInput,
  type TransactionKind,
} from '../../types/api'
import { KIND_LABELS, parseAmountInput, today } from '../../utils/format'
import {
  ErrorMessage,
  FormField,
  inputClass,
  primaryButton,
  secondaryButton,
} from '../ui/FormField'

type Props = {
  categories: Category[]
  /** Edytowana transakcja; brak oznacza dodawanie nowej. */
  initial?: Transaction
  onSubmit: (data: TransactionInput) => Promise<void>
  onCancel?: () => void
}

/** Formularz dodawania i edycji. Kwota jest wpisywana bez znaku, a znak wynika z typu operacji. */
export function TransactionForm({ categories, initial, onSubmit, onCancel }: Props) {
  const isExpense = initial ? initial.amount.startsWith('-') : true
  const [type, setType] = useState<'expense' | 'income'>(isExpense ? 'expense' : 'income')
  const [amount, setAmount] = useState(
    initial ? initial.amount.replace('-', '').replace('.', ',') : '',
  )
  const [date, setDate] = useState(initial?.date ?? today())
  const [description, setDescription] = useState(initial?.description ?? '')
  const [counterparty, setCounterparty] = useState(initial?.counterparty ?? '')
  const [categoryId, setCategoryId] = useState(initial?.category_id?.toString() ?? '')
  const [kind, setKind] = useState<TransactionKind>(initial?.kind ?? 'other')
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  // Dane bankowe z importu są tylko do odczytu, tak jak w API.
  const imported = initial !== undefined && initial.source !== 'manual'

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const parsed = parseAmountInput(amount)
    if (!parsed) {
      setError('Podaj kwotę większą od zera, z co najwyżej dwoma miejscami po przecinku.')
      return
    }
    setError(null)
    setSending(true)
    try {
      await onSubmit({
        date,
        amount: type === 'expense' ? `-${parsed}` : parsed,
        currency: initial?.currency ?? 'PLN',
        description: description.trim(),
        counterparty: counterparty.trim() || null,
        category_id: categoryId ? Number(categoryId) : null,
        kind,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nie udało się zapisać')
    } finally {
      setSending(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      aria-label={initial ? 'Edycja transakcji' : 'Nowa transakcja'}
      className="grid grid-cols-1 gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 md:grid-cols-4"
    >
      <FormField label="Typ">
        <select
          value={type}
          disabled={imported}
          onChange={(e) => setType(e.target.value as 'expense' | 'income')}
          className={inputClass}
        >
          <option value="expense">Wydatek</option>
          <option value="income">Przychód</option>
        </select>
      </FormField>
      <FormField label="Kwota (zł)">
        <input
          inputMode="decimal"
          required
          disabled={imported}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0,00"
          className={inputClass}
        />
      </FormField>
      <FormField label="Data">
        <input
          type="date"
          required
          disabled={imported}
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className={inputClass}
        />
      </FormField>
      <FormField label="Rodzaj">
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value as TransactionKind)}
          className={inputClass}
        >
          {TRANSACTION_KINDS.map((k) => (
            <option key={k} value={k}>
              {KIND_LABELS[k]}
            </option>
          ))}
        </select>
      </FormField>
      <div className="md:col-span-2">
        <FormField label="Opis">
          <input
            required
            maxLength={500}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className={inputClass}
          />
        </FormField>
      </div>
      <FormField label="Kontrahent (opcjonalnie)">
        <input
          maxLength={255}
          disabled={imported}
          value={counterparty}
          onChange={(e) => setCounterparty(e.target.value)}
          className={inputClass}
        />
      </FormField>
      <FormField label="Kategoria">
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className={inputClass}
        >
          <option value="">Bez kategorii</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </FormField>
      <div className="flex flex-col gap-2 md:col-span-4">
        <ErrorMessage message={error} />
        <div className="flex gap-2">
          <button type="submit" disabled={sending} className={primaryButton}>
            {initial ? 'Zapisz zmiany' : 'Dodaj'}
          </button>
          {onCancel && (
            <button type="button" onClick={onCancel} className={secondaryButton}>
              Anuluj
            </button>
          )}
        </div>
      </div>
    </form>
  )
}
