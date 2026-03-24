import { isAxiosError } from 'axios'

/**
 * Extract a human-readable error message from an Axios error response.
 *
 * FastAPI returns validation errors as:
 *   { detail: [{ msg: "Value error, Password must ...", loc: ["body","password"] }] }
 *
 * And regular errors as:
 *   { detail: "Some string message" }
 */
export function parseApiError(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (!isAxiosError(err)) return fallback

  const detail = err.response?.data?.detail
  if (!detail) return fallback

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    return detail
      .map((e: { msg?: string }) => {
        let msg: string = e.msg || String(e)
        // Strip Pydantic's "Value error, " prefix
        msg = msg.replace(/^Value error,\s*/i, '')
        return msg
      })
      .join('. ')
  }

  return fallback
}
