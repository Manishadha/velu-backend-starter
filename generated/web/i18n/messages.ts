// generated/web/i18n/messages.ts
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type I18nSection = {
  id: string;
  heading: string;
  body: string;
  primary_cta?: string;
};

export type I18nLocaleContent = {
  locale: string;
  title: string;
  tagline?: string;
  sections: I18nSection[];
};

export type MessagesSummary = {
  name: string;
  kind: string;
  locales: string[];
};

export type MessagesResponse = {
  locale: string;
  locales: string[];
  messages: Record<string, I18nLocaleContent>;
  summary: MessagesSummary;
};
export type I18nMessagesResponse = MessagesResponse;

function buildUrl(locale?: string): string {
  const base = `${API_BASE}/v1/i18n/messages`;
  if (!locale) {
    return base;
  }
  try {
    const u = new URL(base);
    u.searchParams.set("locale", locale);
    return u.toString();
  } catch {
    return `${base}?locale=${encodeURIComponent(locale)}`;
  }
}

export async function fetchMessages(
  locale?: string,
): Promise<MessagesResponse> {
  const url = buildUrl(locale);
  const res = await fetch(url, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`http ${res.status}`);
  }

  const data = (await res.json()) as MessagesResponse;
  if (!data || !data.messages || !data.locale) {
    throw new Error("invalid i18n payload");
  }
  return data;
}

export async function safeFetchMessages(
  locale?: string,
): Promise<MessagesResponse | null> {
  try {
    return await fetchMessages(locale);
  } catch {
    return null;
  }
}
