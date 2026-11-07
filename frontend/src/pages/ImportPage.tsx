import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type ChangeEvent, useState } from 'react'
import { Link } from 'react-router'
import { importsApi } from '../api/endpoints'
import { ErrorMessage, primaryButton, secondaryButton } from '../components/ui/FormField'
import type { ImportBatch, ImportPreview } from '../types/api'
import { KIND_LABELS, formatAmount, formatDate } from '../utils/format'

const MAX_SIZE_MB = 5

/** Import wyciągu: wybór pliku, podgląd z kontrolą sum, zapis. Plik nie jest przechowywany na serwerze. */
export function ImportPage() {
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [result, setResult] = useState<ImportBatch | null>(null)
  const [error, setError] = useState<string | null>(null)
  const history = useQuery({ queryKey: ['imports'], queryFn: importsApi.history })

  const previewMutation = useMutation({
    mutationFn: importsApi.preview,
    onSuccess: setPreview,
    onError: (err) => setError(err.message),
  })
  const confirmMutation = useMutation({
    mutationFn: importsApi.confirm,
    onSuccess: (batch) => {
      setResult(batch)
      setPreview(null)
      setFile(null)
      queryClient.invalidateQueries({ queryKey: ['imports'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
    onError: (err) => setError(err.message),
  })

  function choose(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0] ?? null
    setPreview(null)
    setResult(null)
    setError(null)
    if (chosen && chosen.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`Plik jest większy niż ${MAX_SIZE_MB} MB.`)
      setFile(null)
      return
    }
    setFile(chosen)
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-slate-900">Import wyciągu</h1>

      <section className="flex flex-col gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
        <p className="text-sm text-slate-600">
          Wybierz miesięczny wyciąg z rachunku ING w formacie PDF. Przed zapisem zobaczysz podgląd,
          a transakcje zaimportowane wcześniej zostaną pominięte.
        </p>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Plik wyciągu (PDF)</span>
          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={choose}
            className="text-sm text-slate-700 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2"
          />
        </label>
        <ErrorMessage message={error} />
        <div>
          <button
            type="button"
            disabled={!file || previewMutation.isPending}
            onClick={() => {
              setError(null)
              if (file) previewMutation.mutate(file)
            }}
            className={primaryButton}
          >
            {previewMutation.isPending ? 'Odczytywanie…' : 'Pokaż podgląd'}
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

      {preview && file && (
        <section aria-label="Podgląd importu" className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat
              label="Okres"
              value={`${formatDate(preview.period_start)} – ${formatDate(preview.period_end)}`}
            />
            <Stat label="Transakcji" value={`${preview.total}`} />
            <Stat label="Nowych" value={`${preview.new}`} />
            <Stat label="Już zaimportowanych" value={`${preview.duplicates}`} />
          </div>
          <p className="rounded-md bg-emerald-50 px-4 py-2 text-sm text-emerald-900">
            Zgodne z sumami kontrolnymi wyciągu: uznania {preview.credits_count} (
            {formatAmount(preview.credits_sum, 'PLN')}), obciążenia {preview.debits_count} (
            {formatAmount(preview.debits_sum, 'PLN')}).
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={preview.new === 0 || confirmMutation.isPending}
              onClick={() => confirmMutation.mutate(file)}
              className={primaryButton}
            >
              {preview.new === 0 ? 'Brak nowych transakcji' : `Zapisz ${preview.new} nowych`}
            </button>
            <button type="button" onClick={() => setPreview(null)} className={secondaryButton}>
              Anuluj
            </button>
          </div>
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
