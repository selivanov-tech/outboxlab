export type Credentials =
  { kind: 'apiKey'; value: string } | { kind: 'workspaceId'; value: string };

const API_KEY = /^olab_[0-9a-f]+_[A-Za-z0-9_-]+$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Reads what a person pasted into the connect form: an API key, or a workspace id for a local API. */
export function parseCredentials(input: string): Credentials | null {
  const value = input.trim();
  if (API_KEY.test(value)) {
    return { kind: 'apiKey', value };
  }
  if (UUID.test(value)) {
    return { kind: 'workspaceId', value: value.toLowerCase() };
  }
  return null;
}

export function authHeaders(credentials: Credentials): Record<string, string> {
  return credentials.kind === 'apiKey'
    ? { Authorization: `Bearer ${credentials.value}` }
    : { 'X-Workspace-Id': credentials.value };
}

export function encodeCredentials(credentials: Credentials): string {
  return `${credentials.kind}:${credentials.value}`;
}

export function decodeCredentials(raw: string | undefined): Credentials | null {
  if (!raw) {
    return null;
  }
  const separator = raw.indexOf(':');
  const kind = raw.slice(0, separator);
  const parsed = parseCredentials(raw.slice(separator + 1));
  return parsed && parsed.kind === kind ? parsed : null;
}

/** A short, safe way to show which credential is in use. */
export function describeCredentials(credentials: Credentials): string {
  if (credentials.kind === 'workspaceId') {
    return `workspace ${credentials.value.slice(0, 8)}`;
  }
  const [scheme, prefix] = credentials.value.split('_');
  return `key ${scheme}_${prefix}`;
}
