'use client';

import { useActionState } from 'react';

import { connect, type ConnectState } from '../model/connect';

const INITIAL: ConnectState = { error: null };

export function ConnectForm() {
  const [state, action, pending] = useActionState(connect, INITIAL);
  return (
    <form action={action} className="form">
      <label htmlFor="credential">API key</label>
      <input
        id="credential"
        name="credential"
        type="password"
        autoComplete="off"
        spellCheck={false}
        required
        placeholder="olab_…"
        aria-describedby="credential-help credential-error"
      />
      <p id="credential-help" className="field-help">
        Create a key with <code>make api-key</code>. A local API also accepts a workspace id.
      </p>
      <p id="credential-error" className="field-error" role="alert">
        {state.error}
      </p>
      <button type="submit" className="button" disabled={pending}>
        {pending ? 'Connecting…' : 'Connect workspace'}
      </button>
    </form>
  );
}
