import type {
  BankProfile,
  Category,
  CsvDelimiter,
  CsvDetection,
  CsvEncoding,
  ImportBatch,
  ImportOptions,
  ImportPreview,
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
