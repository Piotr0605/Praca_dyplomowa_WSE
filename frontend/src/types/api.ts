/** Odpowiedź GET /api/health. */
export type HealthResponse = {
  status: 'ok' | 'degraded'
  database: 'ok' | 'error'
}

export type User = {
  id: number
  email: string
  created_at: string
}

export type Category = {
  id: number
  name: string
  color: string | null
  icon: string | null
  is_income: boolean
  is_system: boolean
}

export const TRANSACTION_KINDS = [
  'card',
  'blik',
  'transfer',
  'own_transfer',
  'refund',
  'cash',
  'fee',
  'other',
] as const
export type TransactionKind = (typeof TRANSACTION_KINDS)[number]

/** Kwota jest tekstem (np. "-12.50"), żeby nie tracić dokładności na liczbach zmiennoprzecinkowych. */
export type Transaction = {
  id: number
  date: string
  booking_date: string | null
  amount: string
  currency: string
  description: string
  counterparty: string | null
  category_id: number | null
  kind: TransactionKind
  source: 'pdf' | 'csv' | 'manual'
  created_at: string
}

export type TransactionInput = {
  date: string
  amount: string
  currency: string
  description: string
  counterparty: string | null
  category_id: number | null
  kind: TransactionKind
}

export type TransactionPage = {
  items: Transaction[]
  total: number
  page: number
  page_size: number
}

export type TransactionFilters = {
  date_from?: string
  date_to?: string
  category_id?: number
  uncategorized?: boolean
  q?: string
  page: number
  page_size: number
}
