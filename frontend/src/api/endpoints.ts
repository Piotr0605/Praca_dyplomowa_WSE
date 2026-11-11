import type {
  AnalyticsByCategory,
  AnalyticsChanges,
  AnalyticsMonth,
  AnalyticsSummary,
  AnalyticsTop,
  BankProfile,
  CategorizationStats,
  Category,
  CategoryInput,
  CategoryRule,
  CsvDelimiter,
  CsvDetection,
  CsvEncoding,
  ImportBatch,
  ImportOptions,
  ImportPreview,
  Period,
  Transaction,
  TransactionFilters,
  TransactionInput,
  TransactionPage,
  User,
} from '../types/api'
import { request } from './client'

export const authApi = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      form: { username: email, password },
    }),
  register: (email: string, password: string) =>
    request<User>('/auth/register', { method: 'POST', json: { email, password } }),
  me: () => request<User>('/auth/me'),
}

export const categoriesApi = {
  list: () => request<Category[]>('/categories'),
  create: (data: CategoryInput) => request<Category>('/categories', { method: 'POST', json: data }),
  update: (id: number, data: Partial<CategoryInput>) =>
    request<Category>(`/categories/${id}`, { method: 'PATCH', json: data }),
  remove: (id: number) => request<void>(`/categories/${id}`, { method: 'DELETE' }),
}

export const categorizationApi = {
  /** Przypisuje kategorie według reguł; `recategorize` przelicza też kategorie nadane wcześniej przez reguły. */
  apply: (recategorize = false) =>
    request<{ categorized: number }>('/categorization/apply', {
      method: 'POST',
      query: { recategorize },
    }),
  stats: () => request<CategorizationStats>('/categorization/stats'),
}

export const rulesApi = {
  list: () => request<CategoryRule[]>('/rules'),
  remove: (id: number) => request<void>(`/rules/${id}`, { method: 'DELETE' }),
}

function importForm(options: ImportOptions): Record<string, string> {
  const form: Record<string, string> = {}
  if (options.profile_key) form.profile_key = options.profile_key
  if (options.profile) form.profile = JSON.stringify(options.profile)
  if (options.save_profile) form.save_profile = 'true'
  return form
}

export const importsApi = {
  detect: (file: File, overrides: { encoding?: CsvEncoding; delimiter?: CsvDelimiter } = {}) => {
    const form: Record<string, string> = {}
    if (overrides.encoding) form.encoding = overrides.encoding
    if (overrides.delimiter) form.delimiter = overrides.delimiter
    return request<CsvDetection>('/imports/detect', { method: 'POST', file, form })
  },
  preview: (file: File, options: ImportOptions = {}) =>
    request<ImportPreview>('/imports/preview', {
      method: 'POST',
      file,
      form: importForm(options),
    }),
  confirm: (file: File, options: ImportOptions = {}) =>
    request<ImportBatch>('/imports/confirm', {
      method: 'POST',
      file,
      form: importForm(options),
    }),
  history: () => request<ImportBatch[]>('/imports'),
  banks: () => request<BankProfile[]>('/imports/banks'),
  deleteBank: (id: number) => request<void>(`/imports/banks/${id}`, { method: 'DELETE' }),
}

export const transactionsApi = {
  list: (filters: TransactionFilters) =>
    request<TransactionPage>('/transactions', { query: filters }),
  create: (data: TransactionInput) =>
    request<Transaction>('/transactions', { method: 'POST', json: data }),
  update: (id: number, data: Partial<TransactionInput>) =>
    request<Transaction>(`/transactions/${id}`, { method: 'PATCH', json: data }),
  remove: (id: number) => request<void>(`/transactions/${id}`, { method: 'DELETE' }),
}

export const analyticsApi = {
  summary: (period: Period) => request<AnalyticsSummary>('/analytics/summary', { query: period }),
  byCategory: (period: Period) =>
    request<AnalyticsByCategory>('/analytics/by-category', { query: period }),
  monthly: (months = 12) => request<AnalyticsMonth[]>('/analytics/monthly', { query: { months } }),
  /** Bez miesiąca: ostatni pełny miesiąc. */
  changes: (month?: string) =>
    request<AnalyticsChanges>('/analytics/changes', { query: { month } }),
  top: (period: Period, limit = 5) =>
    request<AnalyticsTop>('/analytics/top', { query: { ...period, limit } }),
}
