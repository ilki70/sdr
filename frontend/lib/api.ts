export async function fetchJson<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  const text = await response.text();

  if (!response.ok) {
    let message = `Falha na requisicao: ${response.status}`;
    try {
      const payload = text ? (JSON.parse(text) as { detail?: string; message?: string }) : null;
      message = payload?.detail || payload?.message || message;
    } catch {
      if (text) {
        message = text;
      }
    }
    throw new Error(message);
  }

  return (text ? JSON.parse(text) : null) as T;
}
