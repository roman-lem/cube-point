// Версии текстов согласий на странице политики (pages/privacy).
// Меняются вместе с текстом и с CONSENT_VERSIONS в backend/app/consents.py:
// сервер принимает только текущую версию.
export const CONSENT_VERSIONS = {
  processing: '2026-09-26',
  publication: '2026-09-26',
} as const

export interface ConsentChoice {
  processing: boolean
  publication: boolean
}

/** Тело запроса: версия текста у каждого отмеченного согласия. */
export function consentsPayload(choice: ConsentChoice) {
  return {
    processing: choice.processing ? CONSENT_VERSIONS.processing : null,
    publication: choice.publication ? CONSENT_VERSIONS.publication : null,
  }
}

/** Ошибки под чекбоксами, если какое-то согласие не отмечено. */
export function missingConsents(choice: ConsentChoice): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!choice.processing) errors.consent_processing = 'Нужно ваше согласие'
  if (!choice.publication) errors.consent_publication = 'Нужно ваше согласие'
  return errors
}
