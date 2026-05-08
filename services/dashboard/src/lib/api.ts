export function apiFetch(url: string, opts: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('flow_api_token')
  return fetch(url, {
    ...opts,
    headers: {
      ...(token ? { 'X-API-Token': token } : {}),
      ...opts.headers,
    },
  })
}
