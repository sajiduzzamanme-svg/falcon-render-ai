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
  fidelity_score: number | null;
}

export interface RenderDetail extends RenderItem {
  fidelity_attempts: number;
  error: ApiErrorDetail | null;
  artifacts: {
    sketch: string;
    edge: string;
    reference: string | null;
    render: string | null;
    preview: string | null;
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

function authHeaders(token?: string): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

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
  reference?: File | null,
  accessToken?: string,
): Promise<CreateRenderResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("preset", preset);
  form.append("style", style);
  if (reference) form.append("reference", reference);
  return request<CreateRenderResponse>("/api/v1/renders", {
    method: "POST",
    body: form,
    headers: authHeaders(accessToken),
  });
}

export function listRenders(): Promise<ListRendersResponse> {
  return request<ListRendersResponse>("/api/v1/renders");
}

export function getRender(
  id: string,
  accessToken?: string,
): Promise<RenderDetail> {
  return request<RenderDetail>(`/api/v1/renders/${encodeURIComponent(id)}`, {
    headers: authHeaders(accessToken),
  });
}

export function generateRender(
  id: string,
  accessToken?: string,
): Promise<GenerateRenderResponse> {
  return request<GenerateRenderResponse>(
    `/api/v1/renders/${encodeURIComponent(id)}/generate`,
    { method: "POST", headers: authHeaders(accessToken) },
  );
}

export interface DownloadUrlResponse {
  download_url: string;
  expires_in: number | null;
}

/** Signed-in only: mint a download URL for the full-resolution render. */
export function getDownloadUrl(
  id: string,
  accessToken: string,
): Promise<DownloadUrlResponse> {
  return request<DownloadUrlResponse>(
    `/api/v1/renders/${encodeURIComponent(id)}/download`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
}

/**
 * Download the full-resolution render to the user's device.
 * Fetches with the session token (works for both signed Storage URLs and
 * the local-dev direct file URL, which requires the token).
 */
export async function downloadRender(
  id: string,
  accessToken: string,
): Promise<void> {
  const { download_url } = await getDownloadUrl(id, accessToken);
  const res = await fetch(download_url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    throw new ApiError(
      res.status,
      "DOWNLOAD_FAILED",
      `Download failed with HTTP ${res.status}.`,
    );
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  try {
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = `falcon-render-${id}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000);
  }
}
