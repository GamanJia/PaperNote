import { apiRequest } from "./client";
import type {
  AppSettings,
  ExportResponse,
  HistoryDetail,
  HistorySummary,
  SearchRequest,
  SearchResponse,
  SourceItem,
  VenueOptions
} from "../types";
import type { LLMConfig, PaperResult } from "../types";

export function runSearch(payload: SearchRequest): Promise<SearchResponse> {
  return apiRequest<SearchResponse>("/api/search", {
    method: "POST",
    body: JSON.stringify(payload),
    timeoutMs: 180000
  });
}

export function listHistory(): Promise<HistorySummary[]> {
  return apiRequest<HistorySummary[]>("/api/history");
}

export function getHistory(searchId: string): Promise<HistoryDetail> {
  return apiRequest<HistoryDetail>(`/api/history/${searchId}`);
}

export function deleteHistory(searchId: string): Promise<{ ok: boolean }> {
  return apiRequest<{ ok: boolean }>(`/api/history/${searchId}`, {
    method: "DELETE"
  });
}

export function rerunHistory(searchId: string): Promise<SearchResponse> {
  return apiRequest<SearchResponse>(`/api/history/${searchId}/rerun`, {
    method: "POST"
  });
}

export function exportResults(payload: {
  search_id?: string;
  results?: PaperResult[];
  format: "csv" | "xlsx" | "markdown";
  file_prefix?: string;
}): Promise<ExportResponse> {
  return apiRequest<ExportResponse>("/api/export", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getSettings(): Promise<AppSettings> {
  return apiRequest<AppSettings>("/api/settings");
}

export function saveSettings(payload: AppSettings): Promise<AppSettings> {
  return apiRequest<AppSettings>("/api/settings", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function testLLM(model: LLMConfig): Promise<{ ok: boolean; detail: string }> {
  return apiRequest<{ ok: boolean; detail: string }>("/api/settings/llm/test", {
    method: "POST",
    body: JSON.stringify({ model })
  });
}

export function listSources(): Promise<SourceItem[]> {
  return apiRequest<SourceItem[]>("/api/sources");
}

export function listVenueOptions(params?: {
  q?: string;
  limit?: number;
}): Promise<VenueOptions> {
  const searchParams = new URLSearchParams();
  if (params?.q?.trim()) {
    searchParams.set("q", params.q.trim());
  }
  if (typeof params?.limit === "number") {
    searchParams.set("limit", String(params.limit));
  }
  const queryString = searchParams.toString();
  const path = queryString ? `/api/venue-options?${queryString}` : "/api/venue-options";
  return apiRequest<VenueOptions>(path, { timeoutMs: 15000 });
}
