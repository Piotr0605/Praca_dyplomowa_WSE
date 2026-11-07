import type {
  Category,
  ImportBatch,
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

export const importsApi = {
  preview: (file: File) => request<ImportPreview>('/imports/preview', { method: 'POST', file }),
  confirm: (file: File) => request<ImportBatch>('/imports/confirm', { method: 'POST', file }),
  history: () => request<ImportBatch[]>('/imports'),
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
