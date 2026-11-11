import type { TransactionKind } from '../types/api'

export const KIND_LABELS: Record<TransactionKind, string> = {
  card: 'Karta',
  blik: 'BLIK',
  transfer: 'Przelew',
  own_transfer: 'Przelew własny',
  refund: 'Zwrot',
  cash: 'Gotówka',
  fee: 'Opłata',
  other: 'Inne',
}

/** Formatowanie do wyświetlenia. Obliczenia na kwotach wykonuje backend na typie Decimal. */
export function formatAmount(amount: string, currency: string): string {
  return new Intl.NumberFormat('pl-PL', { style: 'currency', currency }).format(Number(amount))
}

/** Kwota w złotych bez groszy, np. na osi wykresu i w kartach. */
export function formatPLN(amount: string | number, fractionDigits = 2): string {
  return new Intl.NumberFormat('pl-PL', {
    style: 'currency',
    currency: 'PLN',
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(Number(amount))
}

/** Ułamek jako procent, np. 0.125 → "12,5%". */
export function formatPercent(fraction: number, fractionDigits = 1): string {
  return new Intl.NumberFormat('pl-PL', {
    style: 'percent',
    maximumFractionDigits: fractionDigits,
  }).format(fraction)
}

const MONTHS = [
  'styczeń',
  'luty',
  'marzec',
  'kwiecień',
  'maj',
  'czerwiec',
  'lipiec',
  'sierpień',
  'wrzesień',
  'październik',
  'listopad',
  'grudzień',
]
const MONTHS_SHORT = [
  'sty',
  'lut',
  'mar',
  'kwi',
  'maj',
  'cze',
  'lip',
  'sie',
  'wrz',
  'paź',
  'lis',
  'gru',
]

/** "2026-10" → "październik 2026" albo, w wersji krótkiej, "paź 2026". */
export function formatMonth(month: string, short = false): string {
  const [year, number] = month.split('-')
  return `${(short ? MONTHS_SHORT : MONTHS)[Number(number) - 1]} ${year}`
}

/** Pierwszy i ostatni dzień miesiąca "RRRR-MM" jako daty RRRR-MM-DD. */
export function monthRange(month: string): { date_from: string; date_to: string } {
  const [year, number] = month.split('-').map(Number)
  const lastDay = new Date(Date.UTC(year, number, 0)).getUTCDate()
  return { date_from: `${month}-01`, date_to: `${month}-${String(lastDay).padStart(2, '0')}` }
}

export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-')
  return `${day}.${month}.${year}`
}

/** Dzisiejsza data w formacie RRRR-MM-DD, w strefie czasowej użytkownika. */
export function today(): string {
  return new Date().toLocaleDateString('sv-SE')
}

/**
 * Zamienia kwotę wpisaną przez użytkownika (np. "1 234,5") na tekst dla API ("1234.50").
 * Zwraca null, gdy wartość nie jest dodatnią kwotą z co najwyżej dwoma miejscami po przecinku.
 */
export function parseAmountInput(input: string): string | null {
  const normalized = input.replace(/\s/g, '').replace(',', '.')
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(normalized)) return null
  const [whole, fraction = ''] = normalized.split('.')
  const result = `${whole.replace(/^0+(?=\d)/, '')}.${fraction.padEnd(2, '0')}`
  return Number(result) > 0 ? result : null
}
