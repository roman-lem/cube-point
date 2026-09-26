// Versions of the consent texts on the policy page (pages/privacy).
// They change together with the text and with CONSENT_VERSIONS in backend/app/consents.py:
// the server accepts only the current version.
export const CONSENT_VERSIONS = {
  processing: '2026-09-26',
  publication: '2026-09-26',
} as const

export interface ConsentChoice {
  processing: boolean
  publication: boolean
}

/** Request body: the text version of each checked consent. */
export function consentsPayload(choice: ConsentChoice) {
  return {
    processing: choice.processing ? CONSENT_VERSIONS.processing : null,
    publication: choice.publication ? CONSENT_VERSIONS.publication : null,
  }
}

/** Errors under the checkboxes if some consent is not checked. */
export function missingConsents(choice: ConsentChoice): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!choice.processing) errors.consent_processing = 'Нужно ваше согласие'
  if (!choice.publication) errors.consent_publication = 'Нужно ваше согласие'
  return errors
}
