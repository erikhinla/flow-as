export function apiFetch(url: string, opts: RequestInit = {}): Promise<Response> {
  return fetch(url, {
    ...opts,
    credentials: 'same-origin',
    headers: opts.headers,
  })
}
