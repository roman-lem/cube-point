import { useRoute, useRouter } from 'vue-router'

/** The token from an address fragment: "#token=…" → "…", otherwise ''. */
export function tokenFromHash(hash: string): string {
  return new URLSearchParams(hash.replace(/^#/, '')).get('token') ?? ''
}

/**
 * The token of a link from a letter: /reset-password#token=…, /confirm-email#token=…
 *
 * The token is in the fragment: the browser never sends it to the server, neither
 * in the request line nor in Referer, so it stays out of server logs. The page
 * posts it to the API in the request body.
 * Letters sent before the change have ?token=…: such a link still works, and the
 * token is moved from the query to the fragment right away, before any request,
 * so it does not stay in the address and history.
 */
export function useLinkToken(): string {
  const route = useRoute()
  const router = useRouter()
  const fromHash = tokenFromHash(route.hash)
  if (fromHash) {
    return fromHash
  }
  const fromQuery = typeof route.query.token === 'string' ? route.query.token : ''
  if (fromQuery) {
    const { token: _, ...query } = route.query
    router.replace({ query, hash: `#token=${encodeURIComponent(fromQuery)}` })
  }
  return fromQuery
}
