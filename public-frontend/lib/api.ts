export type PublicStoryListItem = {
  id: number;
  slug: string;
  title: string;
  subtitle?: string | null;
  dek?: string | null;
  topic?: string | null;
  tags?: string[] | null;
  published_at?: string | null;
  updated_at?: string | null;
  summary?: string | null;
  preview_chart_type?: string | null;
};

export type PublicCorrelationItem = {
  series_title: string;
  comparison_text: string;
  coefficient?: number | null;
};

export type PublicStoryDetail = {
  id: number;
  slug: string;
  title: string;
  subtitle?: string | null;
  dek?: string | null;
  body_markdown: string;
  topic?: string | null;
  tags?: string[] | null;
  primary_chart_spec: Record<string, unknown>;
  secondary_chart_spec?: Record<string, unknown> | null;
  chart_type?: string | null;
  sources?: Array<Record<string, unknown>> | null;
  summary?: string | null;
  chart_public_caption: string;
  analysis_economic: string;
  analysis_social: string;
  correlations: PublicCorrelationItem[];
  published_at?: string | null;
  language: string;
  updated_at: string;
};

export type PublicStoryListResponse = {
  items: PublicStoryListItem[];
  total: number;
  page: number;
  page_size: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_STORIES_API_BASE_URL ?? "http://localhost:8000";

async function fetchFromApi<T>(path: string): Promise<T> {
  const normalizedBase = API_BASE_URL.endsWith("/") ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
  const response = await fetch(`${normalizedBase}${path}`, { next: { revalidate: 60 } });
  if (!response.ok) {
    throw new Error(`Public API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getStories(params?: { page?: number; page_size?: number; topic?: string; tag?: string }): Promise<PublicStoryListResponse> {
  const search = new URLSearchParams();
  search.set("page", String(params?.page ?? 1));
  search.set("page_size", String(params?.page_size ?? 30));
  if (params?.topic) search.set("topic", params.topic);
  if (params?.tag) search.set("tag", params.tag);
  return fetchFromApi<PublicStoryListResponse>(`/public/stories?${search.toString()}`);
}

export function getStoryBySlug(slug: string): Promise<PublicStoryDetail> {
  const safe = encodeURIComponent(slug);
  return fetchFromApi<PublicStoryDetail>(`/public/stories/${safe}`);
}

export function getStoriesByTopic(topic: string, page = 1, page_size = 30): Promise<PublicStoryListResponse> {
  const search = new URLSearchParams();
  search.set("page", String(page));
  search.set("page_size", String(page_size));
  return fetchFromApi<PublicStoryListResponse>(
    `/public/stories/by-topic/${encodeURIComponent(topic)}?${search.toString()}`
  );
}
