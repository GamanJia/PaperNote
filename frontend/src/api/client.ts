const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    if (typeof payload === "string") {
      throw new Error(payload || `Request failed (${response.status})`);
    }
    const detail =
      typeof payload === "object" && payload && "detail" in payload
        ? String((payload as Record<string, unknown>).detail)
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return payload as T;
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });
  return parseResponse<T>(response);
}

export function buildApiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
