/**
 * MSW (Mock Service Worker) handlers for intercepting HTTP requests in tests.
 * Used for component tests that require real network calls.
 */
import { http, HttpResponse } from 'msw'

export const handlers = [
  // Authentication — login/logout/refresh return 204; auth is via HttpOnly cookie.
  http.post('/api/auth/login', () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.post('/api/auth/register', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      id: 1,
      username: body.username ?? 'testuser',
      email: body.email ?? 'test@example.com',
      is_active: true,
    })
  }),

  http.post('/api/auth/logout', () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.post('/api/auth/logout-all', () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.post('/api/auth/refresh', () => {
    return new HttpResponse(null, { status: 204 })
  }),

  // User
  http.get('/api/users/me', () => {
    return HttpResponse.json({
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      is_active: true,
    })
  }),

  http.put('/api/users/me', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      id: 1,
      username: body.username ?? 'testuser',
      email: body.email ?? 'test@example.com',
      is_active: true,
    })
  }),
]

// Error handlers (used in tests that expect an error response)
export const errorHandlers = {
  loginUnauthorized: http.post('/api/auth/login', () => {
    return HttpResponse.json(
      { detail: 'Incorrect username or password' },
      { status: 401 },
    )
  }),

  registerEmailTaken: http.post('/api/auth/register', () => {
    return HttpResponse.json(
      { detail: 'A user with this email already exists' },
      { status: 400 },
    )
  }),

  networkError: http.get('/api/users/me', () => {
    return HttpResponse.error()
  }),
}
