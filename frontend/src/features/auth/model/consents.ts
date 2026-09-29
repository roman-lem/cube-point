// Versions of the consent texts on the policy page (pages/privacy) and of the age
// confirmation below. They change together with the text and with CONSENT_VERSIONS
// in backend/app/consents.py: the server accepts only the current version.
export const CONSENT_VERSIONS = {
  processing: '2026-09-26',
  publication: '2026-09-26',
  age: '2026-09-29',
} as const

// Checkbox text of the age confirmation: under 14, only with a legal representative's consent.
// When it changes, CONSENT_VERSIONS.age changes too.
export const AGE_CONFIRMATION_TEXT =
  'Мне исполнилось 14 лет, или согласие на обработку и распространение моих персональных ' +
  'данных даёт мой законный представитель'

export interface ConsentChoice {
  processing: boolean
  publication: boolean
  age: boolean
}

export function emptyConsents(): ConsentChoice {
  return { processing: false, publication: false, age: false }
}

/** Request body: the text version of each checked consent. */
export function consentsPayload(choice: ConsentChoice) {
  return {
    processing: choice.processing ? CONSENT_VERSIONS.processing : null,
    publication: choice.publication ? CONSENT_VERSIONS.publication : null,
    age: choice.age ? CONSENT_VERSIONS.age : null,
  }
}

/** Errors under the checkboxes if some consent is not checked. */
export function missingConsents(choice: ConsentChoice): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!choice.processing) errors.consent_processing = 'Нужно ваше согласие'
  if (!choice.publication) errors.consent_publication = 'Нужно ваше согласие'
  if (!choice.age) errors.consent_age = 'Нужно подтверждение'
  return errors
}
