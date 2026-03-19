const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
type ApiRequestInit = RequestInit & { timeoutMs?: number };

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

export async function apiRequest<T>(path: string, init?: ApiRequestInit): Promise<T> {
  const timeoutMs = init?.timeoutMs ?? 0;
  const controller = new AbortController();
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  if (timeoutMs > 0) {
    timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  }

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {})
      },
      ...init,
      signal: controller.signal
    });
    return parseResponse<T>(response);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      const seconds = Math.max(1, Math.round(timeoutMs / 1000));
      throw new Error(`请求超时（>${seconds}s），请缩小范围或先关闭 OpenAlex/LLM 筛选重试。`);
    }
    throw error;
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }
}

export function buildApiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
