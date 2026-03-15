/**
 * MSW (Mock Service Worker) handlers for intercepting HTTP requests in tests.
 * Used for component tests that require real network calls.
 */
import { http, HttpResponse } from 'msw'

export const handlers = [
  // Authentication
  http.post('/api/auth/login', () => {
    return HttpResponse.json({
      access_token: 'mock-jwt-token-for-tests',
      token_type: 'bearer',
    })
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
    return HttpResponse.json({ message: 'Successfully logged out' })
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
