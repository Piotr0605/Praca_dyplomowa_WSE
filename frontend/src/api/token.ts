/**
 * Token logowania w sessionStorage: przetrwa odświeżenie strony, a znika po zamknięciu karty.
 * localStorage przechowywałby go dłużej, a zwykła zmienna wylogowywałaby przy każdym odświeżeniu.
 */
const KEY = 'access_token'

export const tokenStore = {
  get: (): string | null => sessionStorage.getItem(KEY),
  set: (token: string): void => sessionStorage.setItem(KEY, token),
  clear: (): void => sessionStorage.removeItem(KEY),
}
