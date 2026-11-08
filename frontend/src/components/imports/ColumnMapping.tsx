import { type ReactElement, useState } from 'react'
import type {
  CsvColumns,
  CsvDelimiter,
  CsvDetection,
  CsvEncoding,
  CsvProfile,
} from '../../types/api'
import {
  ErrorMessage,
  FormField,
  inputClass,
  primaryButton,
  secondaryButton,
} from '../ui/FormField'

type SingleRole = Exclude<keyof CsvColumns, 'description'>

const ROLE_LABELS: Record<SingleRole | 'description' | 'description2', string> = {
  date: 'Data operacji',
  booking_date: 'Data księgowania',
  amount: 'Kwota (ze znakiem)',
  credit: 'Uznania (wpływy)',
  debit: 'Obciążenia (wydatki)',
  currency: 'Waluta',
  description: 'Opis',
  description2: 'Dodatkowy opis',
  counterparty: 'Kontrahent',
  kind: 'Rodzaj operacji',
  reference: 'Numer operacji',
}

const ENCODINGS: [CsvEncoding, string][] = [
  ['utf-8-sig', 'UTF-8'],
  ['cp1250', 'Windows-1250'],
  ['iso-8859-2', 'ISO-8859-2'],
]
const DELIMITERS: [CsvDelimiter, string][] = [
  [';', 'średnik ( ; )'],
  [',', 'przecinek ( , )'],
  ['\t', 'tabulator'],
  ['|', 'kreska ( | )'],
]
const DATE_FORMATS: [string, string][] = [
  ['%Y-%m-%d', 'RRRR-MM-DD'],
  ['%d.%m.%Y', 'DD.MM.RRRR'],
  ['%d-%m-%Y', 'DD-MM-RRRR'],
  ['%d/%m/%Y', 'DD/MM/RRRR'],
  ['%Y.%m.%d', 'RRRR.MM.DD'],
  ['%Y/%m/%d', 'RRRR/MM/DD'],
  ['%m/%d/%Y', 'MM/DD/RRRR'],
]

type Props = {
  detection: CsvDetection
  pending: boolean
  error: string | null
  onRedetect: (overrides: { encoding: CsvEncoding; delimiter: CsvDelimiter }) => void
  onSubmit: (profile: CsvProfile, save: boolean) => void
  onCancel: () => void
}

/**
 * Kreator mapowania kolumn dla pliku CSV, który nie pasuje do żadnego profilu. Pola są wypełnione
 * propozycją z backendu (`/imports/detect`); użytkownik ją potwierdza albo poprawia na podstawie
 * przykładowych wierszy pliku.
 */
export function ColumnMapping({
  detection,
  pending,
  error,
  onRedetect,
  onSubmit,
  onCancel,
}: Props) {
  const suggested = detection.columns
  const [bankName, setBankName] = useState('')
  const [split, setSplit] = useState(!suggested.amount && !!suggested.credit && !!suggested.debit)
  const [columns, setColumns] = useState<Record<SingleRole, string>>(() => ({
    date: suggested.date ?? '',
    booking_date: suggested.booking_date ?? '',
    amount: suggested.amount ?? '',
    credit: suggested.credit ?? '',
    debit: suggested.debit ?? '',
    currency: suggested.currency ?? '',
    counterparty: suggested.counterparty ?? '',
    kind: suggested.kind ?? '',
    reference: suggested.reference ?? '',
  }))
  const [description, setDescription] = useState([
    suggested.description[0] ?? '',
    suggested.description[1] ?? '',
  ])
  const [dateFormat, setDateFormat] = useState(detection.date_format ?? '')
  const [decimal, setDecimal] = useState(detection.decimal_separator)
  const [save, setSave] = useState(true)

  const roleOf = new Map<string, string>()
  const activeRoles: SingleRole[] = [
    'date',
    'booking_date',
    ...(split ? (['credit', 'debit'] as const) : (['amount'] as const)),
    'currency',
    'counterparty',
    'kind',
    'reference',
  ]
  for (const role of activeRoles) if (columns[role]) roleOf.set(columns[role], ROLE_LABELS[role])
  if (description[0]) roleOf.set(description[0], ROLE_LABELS.description)
  if (description[1]) roleOf.set(description[1], ROLE_LABELS.description2)

  const problems = [
    !bankName.trim() && 'nazwę banku',
    !columns.date && 'kolumnę daty',
    !dateFormat && 'format daty',
    !description[0] && 'kolumnę opisu',
    split
      ? (!columns.credit || !columns.debit) && 'kolumny uznań i obciążeń'
      : !columns.amount && 'kolumnę kwoty',
  ].filter(Boolean)

  function submit() {
    const chosen: Partial<Record<SingleRole, string>> = {}
    for (const role of activeRoles) if (columns[role]) chosen[role] = columns[role]
    onSubmit(
      {
        bank_name: bankName.trim(),
        encoding: detection.encoding,
        delimiter: detection.delimiter,
        date_format: dateFormat,
        decimal_separator: decimal,
        columns: {
          ...chosen,
          date: columns.date,
          description: [...new Set(description.filter(Boolean))],
        },
      },
      save,
    )
  }

  function columnSelect(
    value: string,
    onChange: (value: string) => void,
  ): ReactElement<{ id?: string }> {
    return (
      <select value={value} onChange={(e) => onChange(e.target.value)} className={inputClass}>
        <option value="">— brak —</option>
        {detection.headers.map((header) => (
          <option key={header} value={header}>
            {header}
          </option>
        ))}
      </select>
    )
  }

  function roleField(role: SingleRole) {
    return (
      <FormField key={role} label={ROLE_LABELS[role]}>
        {columnSelect(columns[role], (value) => setColumns({ ...columns, [role]: value }))}
      </FormField>
    )
  }

  return (
    <section
      aria-label="Mapowanie kolumn"
      className="flex flex-col gap-4 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200"
    >
      <div>
        <h2 className="text-base font-semibold text-slate-900">Mapowanie kolumn</h2>
        <p className="text-sm text-slate-600">
          Ten format pliku nie jest jeszcze zapisany, więc kolumny zostały rozpoznane automatycznie.
          Sprawdź propozycję na przykładowych wierszach, wpisz nazwę banku i w razie potrzeby popraw
          kolumny. Po zapisaniu profilu kolejne pliki z tego banku zostaną rozpoznane bez tego
          kroku.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <FormField label="Nazwa banku">
          <input
            value={bankName}
            maxLength={100}
            onChange={(e) => setBankName(e.target.value)}
            placeholder="np. mBank"
            className={inputClass}
          />
        </FormField>
        <FormField label="Kodowanie znaków">
          <select
            value={detection.encoding}
            onChange={(e) =>
              onRedetect({
                encoding: e.target.value as CsvEncoding,
                delimiter: detection.delimiter,
              })
            }
            className={inputClass}
          >
            {ENCODINGS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Separator kolumn">
          <select
            value={detection.delimiter}
            onChange={(e) =>
              onRedetect({
                encoding: detection.encoding,
                delimiter: e.target.value as CsvDelimiter,
              })
            }
            className={inputClass}
          >
            {DELIMITERS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      <div className="overflow-auto rounded-md ring-1 ring-slate-200">
        <table className="w-full text-left text-xs">
          <caption className="sr-only">Przykładowe wiersze pliku</caption>
          <thead className="bg-slate-50 text-slate-700">
            <tr>
              {detection.headers.map((header) => (
                <th key={header} scope="col" className="whitespace-nowrap px-2 py-1 font-medium">
                  {header}
                  <span className="block font-normal text-emerald-700">
                    {roleOf.get(header) ?? ' '}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {detection.sample_rows.map((row, index) => (
              <tr key={index} className="border-t border-slate-100">
                {detection.headers.map((header, column) => (
                  <td
                    key={header}
                    className={`max-w-48 truncate whitespace-nowrap px-2 py-1 ${roleOf.has(header) ? 'text-slate-900' : 'text-slate-400'}`}
                  >
                    {row[column] ?? ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <fieldset className="flex flex-wrap gap-4 text-sm">
        <legend className="mb-1 font-medium text-slate-700">Kwota w pliku</legend>
        <label className="flex items-center gap-2">
          <input type="radio" checked={!split} onChange={() => setSplit(false)} />
          jedna kolumna, wydatki ze znakiem minus
        </label>
        <label className="flex items-center gap-2">
          <input type="radio" checked={split} onChange={() => setSplit(true)} />
          osobne kolumny uznań i obciążeń
        </label>
      </fieldset>

      <div className="grid gap-3 md:grid-cols-3">
        {roleField('date')}
        {roleField('booking_date')}
        <FormField label="Format daty">
          <select
            value={dateFormat}
            onChange={(e) => setDateFormat(e.target.value)}
            className={inputClass}
          >
            <option value="">— wybierz —</option>
            {DATE_FORMATS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </FormField>
        {split ? [roleField('credit'), roleField('debit')] : roleField('amount')}
        <FormField label="Separator dziesiętny">
          <select
            value={decimal}
            onChange={(e) => setDecimal(e.target.value as ',' | '.')}
            className={inputClass}
          >
            <option value=",">przecinek (1 234,56)</option>
            <option value=".">kropka (1,234.56)</option>
          </select>
        </FormField>
        <FormField label={ROLE_LABELS.description}>
          {columnSelect(description[0], (value) => setDescription([value, description[1]]))}
        </FormField>
        <FormField label={ROLE_LABELS.description2}>
          {columnSelect(description[1], (value) => setDescription([description[0], value]))}
        </FormField>
        {roleField('counterparty')}
        {roleField('currency')}
        {roleField('kind')}
        {roleField('reference')}
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} />
        Zapamiętaj ustawienia jako profil banku (zapis po zatwierdzeniu importu)
      </label>

      {problems.length > 0 && (
        <p className="text-sm text-slate-600">Uzupełnij: {problems.join(', ')}.</p>
      )}
      <ErrorMessage message={error} />
      <div className="flex gap-2">
        <button
          type="button"
          disabled={problems.length > 0 || pending}
          onClick={submit}
          className={primaryButton}
        >
          {pending ? 'Odczytywanie…' : 'Pokaż podgląd'}
        </button>
        <button type="button" onClick={onCancel} className={secondaryButton}>
          Anuluj
        </button>
      </div>
    </section>
  )
}
