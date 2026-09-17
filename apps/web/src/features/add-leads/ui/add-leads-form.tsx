'use client';

import { useActionState } from 'react';

import { add, type AddLeadsState } from '../model/add';

interface AddLeadsFormProps {
  campaignId: string;
  campaignActive: boolean;
}

const INITIAL: AddLeadsState = { tone: 'idle', message: null, text: '' };

export function AddLeadsForm({ campaignId, campaignActive }: AddLeadsFormProps) {
  const [state, action, pending] = useActionState(add.bind(null, campaignId), INITIAL);
  return (
    <form action={action} className="form">
      <label htmlFor="emails">Lead email addresses</label>
      <textarea
        id="emails"
        name="emails"
        rows={4}
        required
        defaultValue={state.text}
        spellCheck={false}
        placeholder={'ada@example.com\ngrace@example.com'}
        aria-describedby="emails-help"
      />
      <p id="emails-help" className="field-help">
        One per line, or separated by commas.{' '}
        {campaignActive
          ? 'The campaign is active, so new leads are scheduled at once.'
          : 'Nothing is sent until you start the campaign.'}
      </p>
      <button type="submit" className="button button--secondary" disabled={pending}>
        {pending ? 'Adding…' : 'Add leads'}
      </button>
      <p className={`form-message form-message--${state.tone}`} role="status">
        {state.message}
      </p>
    </form>
  );
}
