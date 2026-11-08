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

export type ImportPreviewRow = {
  date: string
  booking_date: string | null
  amount: string
  currency: string
  description: string
  counterparty: string | null
  kind: TransactionKind
  duplicate: boolean
}

export type ImportPreview = {
  format: 'pdf' | 'csv'
  bank: string
  period_start: string
  period_end: string
  /** Salda i sumy kontrolne podaje tylko wyciąg PDF (`verified`). */
  opening_balance: string | null
  closing_balance: string | null
  verified: boolean
  credits_count: number
  credits_sum: string
  debits_count: number
  debits_sum: string
  total: number
  new: number
  duplicates: number
  skipped: number
  transactions: ImportPreviewRow[]
}

export type BankProfile = {
  key: string
  bank_name: string
  builtin: boolean
}

export type CsvColumns = {
  date: string | null
  booking_date: string | null
  amount: string | null
  credit: string | null
  debit: string | null
  currency: string | null
  description: string[]
  counterparty: string | null
  kind: string | null
  reference: string | null
}

export type CsvEncoding = 'utf-8-sig' | 'cp1250' | 'iso-8859-2'
export type CsvDelimiter = ';' | ',' | '\t' | '|'

export type CsvDetection = {
  encoding: CsvEncoding
  delimiter: CsvDelimiter
  header_row: number
  headers: string[]
  sample_rows: string[][]
  columns: CsvColumns
  date_format: string | null
  decimal_separator: ',' | '.'
  missing: string[]
  matched: BankProfile | null
}

/** Ustawienia z kreatora mapowania; backend sprawdza je modelem `CsvProfile`. */
export type CsvProfile = {
  bank_name: string
  encoding: CsvEncoding
  delimiter: CsvDelimiter
  date_format: string
  decimal_separator: ',' | '.'
  columns: Partial<Omit<CsvColumns, 'description'>> & { date: string; description: string[] }
}

/** Jak odczytać plik: PDF i rozpoznane CSV bez opcji, nowe CSV z ustawieniami z kreatora. */
export type ImportOptions = {
  profile_key?: string
  profile?: CsvProfile
  save_profile?: boolean
}

export type ImportBatch = {
  id: number
  bank: string
  filename: string
  rows_total: number
  rows_imported: number
  rows_duplicated: number
  created_at: string
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
