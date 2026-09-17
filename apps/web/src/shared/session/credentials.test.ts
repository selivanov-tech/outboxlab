import { describe, expect, it } from 'vitest';

import {
  authHeaders,
  decodeCredentials,
  describeCredentials,
  encodeCredentials,
  parseCredentials,
} from './credentials';

const KEY = 'olab_7bd848a1caa2_Zm9vLWJhcl9iYXo';
const WORKSPACE = '019e5f2a-1a6d-7fa2-8bee-55d3e1ccdc3d';

describe('parseCredentials', () => {
  it('reads an API key', () => {
    expect(parseCredentials(`  ${KEY}\n`)).toEqual({ kind: 'apiKey', value: KEY });
  });

  it('reads a workspace id and lowercases it', () => {
    expect(parseCredentials(WORKSPACE.toUpperCase())).toEqual({
      kind: 'workspaceId',
      value: WORKSPACE,
    });
  });

  it('rejects anything else', () => {
    expect(parseCredentials('')).toBeNull();
    expect(parseCredentials('olab_key')).toBeNull();
    expect(parseCredentials('Bearer olab_aa_bb')).toBeNull();
  });
});

describe('authHeaders', () => {
  it('sends an API key as a bearer token', () => {
    expect(authHeaders({ kind: 'apiKey', value: KEY })).toEqual({
      Authorization: `Bearer ${KEY}`,
    });
  });

  it('sends a workspace id in its own header', () => {
    expect(authHeaders({ kind: 'workspaceId', value: WORKSPACE })).toEqual({
      'X-Workspace-Id': WORKSPACE,
    });
  });
});

describe('cookie round trip', () => {
  it('restores what it stored', () => {
    const credentials = { kind: 'apiKey', value: KEY } as const;
    expect(decodeCredentials(encodeCredentials(credentials))).toEqual(credentials);
  });

  it('ignores a cookie whose kind and value disagree', () => {
    expect(decodeCredentials(`workspaceId:${KEY}`)).toBeNull();
    expect(decodeCredentials(undefined)).toBeNull();
    expect(decodeCredentials('garbage')).toBeNull();
  });
});

describe('describeCredentials', () => {
  it('never shows the secret part of a key', () => {
    expect(describeCredentials({ kind: 'apiKey', value: KEY })).toBe('key olab_7bd848a1caa2');
  });

  it('shortens a workspace id', () => {
    expect(describeCredentials({ kind: 'workspaceId', value: WORKSPACE })).toBe(
      'workspace 019e5f2a',
    );
  });
});
