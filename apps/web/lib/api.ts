/**
 * Typed client for the Falcon Render AI backend (Phase 1 API contract).
 * Base: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
 */

export const API_BASE: string =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Preset = "daylight" | "dusk" | "night";
export type Style = "modern" | "minimalist" | "warm";
export type RenderStatus = "queued" | "processing" | "succeeded" | "failed";

export interface ApiErrorDetail {
  code: string;
  message: string;
}

/** Typed error thrown by every function below on HTTP or network failure. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export interface Health {
  status: string;
  version: string;
  geometry: string;
  render_provider: string;
}

export interface RenderItem {
  id: string;
  status: RenderStatus;
  preset: Preset;
  style: Style;
  created_at: string;
  updated_at: string;
}

export interface RenderDetail extends RenderItem {
  error: ApiErrorDetail | null;
  artifacts: {
    sketch: string;
    edge: string;
    render: string | null;
  };
}

export interface CreateRenderResponse {
  id: string;
  status: RenderStatus;
  preset: Preset;
  style: Style;
  created_at: string;
}

export interface ListRendersResponse {
  items: RenderItem[];
  total: number;
}

export interface GenerateRenderResponse {
  id: string;
  status: RenderStatus;
}

interface BackendErrorBody {
  error?: {
    code?: string;
    message?: string;
  };
}

const NETWORK_FAILURE_MESSAGE =
  "Could not reach the API server. Make sure the backend is running and NEXT_PUBLIC_API_URL is correct.";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", NETWORK_FAILURE_MESSAGE);
  }

  if (!res.ok) {
    let code = "UNKNOWN_ERROR";
    let message = `Request failed with HTTP ${res.status}.`;
    try {
      const body = (await res.json()) as BackendErrorBody;
      if (body?.error) {
        if (typeof body.error.code === "string") code = body.error.code;
        if (typeof body.error.message === "string") message = body.error.message;
      }
    } catch {
      // Non-JSON error body — keep the default message.
    }
    throw new ApiError(res.status, code, message);
  }

  return (await res.json()) as T;
}

/** Absolute URL for an artifact path such as /api/v1/files/{id}/sketch. */
export function fileUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export function getHealth(): Promise<Health> {
  return request<Health>("/api/v1/health");
}

export function createRender(
  file: File,
  preset: Preset,
  style: Style,
): Promise<CreateRenderResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("preset", preset);
  form.append("style", style);
  return request<CreateRenderResponse>("/api/v1/renders", {
    method: "POST",
    body: form,
  });
}

export function listRenders(): Promise<ListRendersResponse> {
  return request<ListRendersResponse>("/api/v1/renders");
}

export function getRender(id: string): Promise<RenderDetail> {
  return request<RenderDetail>(`/api/v1/renders/${encodeURIComponent(id)}`);
}

export function generateRender(id: string): Promise<GenerateRenderResponse> {
  return request<GenerateRenderResponse>(
    `/api/v1/renders/${encodeURIComponent(id)}/generate`,
    { method: "POST" },
  );
}
