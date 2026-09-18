'use client';

import { useActionState, useState } from 'react';

import { create, type CreateCampaignState } from '../model/create';
import { DELAY_UNITS } from '../model/parse-campaign';

const INITIAL: CreateCampaignState = { errors: null, message: null, values: null };

let nextStepKey = 2;

export function CreateCampaignForm() {
  const [state, action, pending] = useActionState(create, INITIAL);
  const [stepKeys, setStepKeys] = useState([1]);

  return (
    <form action={action} className="form form--wide">
      <label htmlFor="name">Campaign name</label>
      <input
        id="name"
        name="name"
        type="text"
        maxLength={200}
        required
        autoComplete="off"
        defaultValue={state.values?.name}
      />
      <p className="field-error" role="alert">
        {state.errors?.name}
      </p>

      <ol className="step-editor">
        {stepKeys.map((key, index) => {
          const errors = state.errors?.steps[index];
          const typed = state.values?.steps[index];
          return (
            <li key={key} className="step-editor-item">
              <div className="step-editor-head">
                <span className="step-number">{index + 1}</span>
                <h2>{index === 0 ? 'First email' : 'Follow-up'}</h2>
                {stepKeys.length > 1 && (
                  <button
                    type="button"
                    className="button button--quiet"
                    onClick={() => setStepKeys(stepKeys.filter((other) => other !== key))}
                  >
                    Remove step
                  </button>
                )}
              </div>
              <div className="delay-row">
                <label htmlFor={`delayAmount-${key}`}>
                  {index === 0 ? 'Wait after the campaign starts' : 'Wait after the previous step'}
                </label>
                <input
                  id={`delayAmount-${key}`}
                  name="delayAmount"
                  type="number"
                  min={0}
                  step={1}
                  defaultValue={typed?.delayAmount ?? (index === 0 ? 0 : 1)}
                  inputMode="numeric"
                />
                <select
                  name="delayUnit"
                  defaultValue={typed?.delayUnit ?? (index === 0 ? 'minutes' : 'days')}
                  aria-label="Unit"
                >
                  {Object.keys(DELAY_UNITS).map((unit) => (
                    <option key={unit} value={unit}>
                      {unit}
                    </option>
                  ))}
                </select>
              </div>
              <p className="field-error" role="alert">
                {errors?.delay}
              </p>
              <label htmlFor={`subject-${key}`}>Subject</label>
              <input
                id={`subject-${key}`}
                name="subject"
                type="text"
                required
                autoComplete="off"
                defaultValue={typed?.subject}
              />
              <p className="field-error" role="alert">
                {errors?.subject}
              </p>
              <label htmlFor={`body-${key}`}>Email</label>
              <textarea
                id={`body-${key}`}
                name="body"
                rows={7}
                required
                defaultValue={typed?.body}
              />
              <p className="field-error" role="alert">
                {errors?.body}
              </p>
            </li>
          );
        })}
      </ol>

      <div className="form-actions">
        <button
          type="button"
          className="button button--secondary"
          onClick={() => setStepKeys([...stepKeys, nextStepKey++])}
        >
          Add a follow-up
        </button>
        <button type="submit" className="button" disabled={pending}>
          {pending ? 'Saving…' : 'Save as draft'}
        </button>
      </div>
      <p className="form-message" role="alert">
        {state.message}
      </p>
    </form>
  );
}
