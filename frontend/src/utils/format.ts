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
