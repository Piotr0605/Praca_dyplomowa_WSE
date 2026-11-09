import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type ChangeEvent, useState } from 'react'
import { Link } from 'react-router'
import { importsApi } from '../api/endpoints'
import { ColumnMapping } from '../components/imports/ColumnMapping'
import { ErrorMessage, primaryButton, secondaryButton } from '../components/ui/FormField'
import type {
  CsvDelimiter,
  CsvDetection,
  CsvEncoding,
  ImportBatch,
  ImportOptions,
  ImportPreview,
} from '../types/api'
import { KIND_LABELS, formatAmount, formatDate } from '../utils/format'

const MAX_SIZE_MB = 5

function isPdf(file: File): boolean {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}

/**
 * Import wyciągu: wybór pliku, w razie potrzeby mapowanie kolumn CSV, podgląd i zapis.
 * Plik nie jest przechowywany na serwerze: podgląd i zapis wysyłają go osobno.
 */
export function ImportPage() {
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [detection, setDetection] = useState<CsvDetection | null>(null)
  const [options, setOptions] = useState<ImportOptions>({})
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [result, setResult] = useState<ImportBatch | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Nowy klucz czyści pole pliku: bez tego ponowny wybór tego samego pliku nie wywołuje zdarzenia.
  const [inputKey, setInputKey] = useState(0)
  const history = useQuery({ queryKey: ['imports'], queryFn: importsApi.history })
  const banks = useQuery({ queryKey: ['banks'], queryFn: importsApi.banks })

  const previewMutation = useMutation({
    mutationFn: ({ file, options }: { file: File; options: ImportOptions }) =>
      importsApi.preview(file, options).then((data) => ({ data, options })),
    onSuccess: ({ data, options }) => {
      setOptions(options)
      setPreview(data)
      setDetection(null)
    },
    onError: (err) => setError(err.message),
  })
  const detectMutation = useMutation({
    mutationFn: ({
      file,
      overrides,
    }: {
      file: File
      overrides?: { encoding: CsvEncoding; delimiter: CsvDelimiter }
    }) => importsApi.detect(file, overrides),
    onSuccess: (found, { file }) => {
      if (found.matched)
        previewMutation.mutate({ file, options: { profile_key: found.matched.key } })
      else setDetection(found)
    },
    onError: (err) => setError(err.message),
  })
  const confirmMutation = useMutation({
    mutationFn: ({ file, options }: { file: File; options: ImportOptions }) =>
      importsApi.confirm(file, options),
    onSuccess: (batch) => {
      setResult(batch)
      reset()
      queryClient.invalidateQueries({ queryKey: ['imports'] })
      queryClient.invalidateQueries({ queryKey: ['banks'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
    onError: (err) => setError(err.message),
  })
  const deleteBankMutation = useMutation({
    mutationFn: importsApi.deleteBank,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['banks'] }),
    onError: (err) => setError(err.message),
  })

  function reset() {
    setPreview(null)
    setDetection(null)
    setOptions({})
    setFile(null)
    setInputKey((key) => key + 1)
  }

  function choose(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0] ?? null
    setPreview(null)
    setDetection(null)
    setResult(null)
    setError(null)
    if (chosen && chosen.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`Plik jest większy niż ${MAX_SIZE_MB} MB.`)
      setFile(null)
      return
    }
    setFile(chosen)
  }

  function start() {
    if (!file) return
    // Nowe odczytanie zastępuje poprzedni podgląd: kreator i podgląd nie mogą być widoczne naraz.
    setError(null)
    setPreview(null)
    setResult(null)
    if (isPdf(file)) previewMutation.mutate({ file, options: {} })
    else detectMutation.mutate({ file })
  }

  const reading = previewMutation.isPending || detectMutation.isPending
  const ownBanks = (banks.data ?? []).filter((bank) => !bank.builtin)

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-slate-900">Import wyciągu</h1>

      <section className="flex flex-col gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
        <p className="text-sm text-slate-600">
          Wybierz miesięczny wyciąg z ING w formacie PDF albo plik CSV z historią rachunku z
          dowolnego banku. Przed zapisem zobaczysz podgląd, a transakcje zaimportowane wcześniej
          zostaną pominięte.
        </p>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Plik (PDF lub CSV)</span>
          <input
            key={inputKey}
            type="file"
            accept="application/pdf,.pdf,text/csv,.csv,.txt"
            onChange={choose}
            className="text-sm text-slate-700 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2"
          />
        </label>
        {!detection && <ErrorMessage message={error} />}
        <div>
          <button
            type="button"
            disabled={!file || reading || !!detection}
            onClick={start}
            className={primaryButton}
          >
            {reading && !detection ? 'Odczytywanie…' : 'Pokaż podgląd'}
          </button>
        </div>
      </section>

      {result && (
        <p role="status" className="rounded-md bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          Zapisano {result.rows_imported} nowych transakcji, pominięto {result.rows_duplicated}{' '}
          zaimportowanych wcześniej.{' '}
          <Link to="/transactions" className="font-medium underline">
            Przejdź do transakcji
          </Link>
        </p>
      )}

      {detection && file && (
        <ColumnMapping
          key={`${detection.encoding}${detection.delimiter}`}
          detection={detection}
          pending={reading}
          error={error}
          onRedetect={(overrides) => {
            setError(null)
            detectMutation.mutate({ file, overrides })
          }}
          onSubmit={(profile, save) => {
            setError(null)
            previewMutation.mutate({ file, options: { profile, save_profile: save } })
          }}
          onCancel={() => {
            setDetection(null)
            setError(null)
          }}
        />
      )}

      {preview && file && (
        <section aria-label="Podgląd importu" className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <Stat label="Bank" value={`${preview.bank} (${preview.format.toUpperCase()})`} />
            <Stat
              label="Okres"
              value={`${formatDate(preview.period_start)} – ${formatDate(preview.period_end)}`}
            />
            <Stat label="Transakcji" value={`${preview.total}`} />
            <Stat label="Nowych" value={`${preview.new}`} />
            <Stat label="Już zaimportowanych" value={`${preview.duplicates}`} />
          </div>
          {preview.verified ? (
            <p className="rounded-md bg-emerald-50 px-4 py-2 text-sm text-emerald-900">
              Zgodne z sumami kontrolnymi wyciągu: uznania {preview.credits_count} (
              {formatAmount(preview.credits_sum, 'PLN')}), obciążenia {preview.debits_count} (
              {formatAmount(preview.debits_sum, 'PLN')}).
            </p>
          ) : (
            <p className="rounded-md bg-amber-50 px-4 py-2 text-sm text-amber-900">
              Plik CSV nie zawiera sum kontrolnych. Porównaj z historią w banku: uznania{' '}
              {preview.credits_count} ({formatAmount(preview.credits_sum, 'PLN')}), obciążenia{' '}
              {preview.debits_count} ({formatAmount(preview.debits_sum, 'PLN')}).
              {preview.skipped > 0 &&
                ` Pominięto ${preview.skipped} wierszy bez kwoty (np. blokady kartowe).`}
            </p>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={preview.new === 0 || confirmMutation.isPending}
              onClick={() => confirmMutation.mutate({ file, options })}
              className={primaryButton}
            >
              {preview.new === 0 ? 'Brak nowych transakcji' : `Zapisz ${preview.new} nowych`}
            </button>
            <button type="button" onClick={() => setPreview(null)} className={secondaryButton}>
              Anuluj
            </button>
          </div>
          <ErrorMessage message={error} />
          <div className="max-h-[28rem] overflow-auto rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 border-b border-slate-200 bg-white text-slate-600">
                <tr>
                  <th scope="col" className="px-4 py-2 font-medium">
                    Data
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    Opis
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    Rodzaj
                  </th>
                  <th scope="col" className="px-4 py-2 text-right font-medium">
                    Kwota
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {preview.transactions.map((t, index) => (
                  <tr
                    key={index}
                    className={`border-b border-slate-100 ${t.duplicate ? 'text-slate-400' : ''}`}
                  >
                    <td className="whitespace-nowrap px-4 py-2">{formatDate(t.date)}</td>
                    <td className="px-4 py-2">
                      {t.description}
                      {t.counterparty && (
                        <span className="block text-xs text-slate-500">{t.counterparty}</span>
                      )}
                    </td>
                    <td className="px-4 py-2">{KIND_LABELS[t.kind]}</td>
                    <td className="whitespace-nowrap px-4 py-2 text-right tabular-nums">
                      {formatAmount(t.amount, t.currency)}
                    </td>
                    <td className="px-4 py-2">{t.duplicate ? 'już zaimportowana' : 'nowa'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section aria-label="Historia importów" className="flex flex-col gap-2">
        <h2 className="text-base font-semibold text-slate-900">Historia importów</h2>
        {history.data && history.data.length === 0 && (
          <p className="text-sm text-slate-500">Nie zaimportowano jeszcze żadnego wyciągu.</p>
        )}
        {history.data && history.data.length > 0 && (
          <ul className="divide-y divide-slate-100 rounded-xl bg-white text-sm shadow-sm ring-1 ring-slate-200">
            {history.data.map((batch) => (
              <li key={batch.id} className="flex justify-between gap-4 px-4 py-2">
                <span className="text-slate-700">
                  {batch.filename} <span className="text-slate-400">({batch.bank})</span>
                </span>
                <span className="text-slate-600">
                  nowych {batch.rows_imported}, pominiętych {batch.rows_duplicated} ·{' '}
                  {new Date(batch.created_at).toLocaleString('pl-PL')}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Profile banków" className="flex flex-col gap-2">
        <h2 className="text-base font-semibold text-slate-900">Profile plików CSV</h2>
        <p className="text-sm text-slate-500">
          Wbudowane:{' '}
          {(banks.data ?? [])
            .filter((b) => b.builtin)
            .map((b) => b.bank_name)
            .join(', ') || '—'}
          .{ownBanks.length === 0 && ' Nie zapisano jeszcze własnych profili.'}
        </p>
        {ownBanks.length > 0 && (
          <ul className="divide-y divide-slate-100 rounded-xl bg-white text-sm shadow-sm ring-1 ring-slate-200">
            {ownBanks.map((bank) => (
              <li key={bank.key} className="flex items-center justify-between gap-4 px-4 py-2">
                <span className="text-slate-700">{bank.bank_name}</span>
                <button
                  type="button"
                  aria-label={`Usuń profil ${bank.bank_name}`}
                  disabled={deleteBankMutation.isPending}
                  onClick={() => {
                    if (window.confirm(`Usunąć profil „${bank.bank_name}”?`))
                      deleteBankMutation.mutate(Number(bank.key.split(':')[1]))
                  }}
                  className="text-sm text-red-700 hover:underline disabled:opacity-50"
                >
                  Usuń
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white p-3 shadow-sm ring-1 ring-slate-200">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-base font-semibold text-slate-900">{value}</p>
    </div>
  )
}
