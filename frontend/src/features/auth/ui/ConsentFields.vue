<script setup lang="ts">
import type { FieldErrors } from '@/shared/api'
import { AGE_CONFIRMATION_TEXT, type ConsentChoice } from '../model/consents'

// Two separate consents: to processing and to publication (Art. 10.1 of Russian
// Federal Law 152-FZ requires the latter to be separate), and the age confirmation. The full texts are on the policy page
// and the publication consent page. Links open in a new
// tab so the filled-in form is not lost.
const choice = defineModel<ConsentChoice>({ required: true })
defineProps<{ errors: FieldErrors }>()
</script>

<template>
  <div class="consent-fields">
    <div>
      <label class="consent-fields__option">
        <input v-model="choice.processing" type="checkbox" />
        <span>
          Даю согласие на обработку персональных данных на условиях
          <RouterLink :to="{ name: 'privacy', hash: '#processing' }" target="_blank">
            политики обработки персональных данных
          </RouterLink>
        </span>
      </label>
      <p v-if="errors.consent_processing" class="consent-fields__error">
        {{ errors.consent_processing }}
      </p>
    </div>
    <div>
      <label class="consent-fields__option">
        <input v-model="choice.publication" type="checkbox" />
        <span>
          Даю согласие на
          <RouterLink :to="{ name: 'publication-consent' }" target="_blank">
            публикацию
          </RouterLink>
          отображаемого имени и результатов в открытом доступе: в таблицах результатов,
          рекордах и профиле
        </span>
      </label>
      <p v-if="errors.consent_publication" class="consent-fields__error">
        {{ errors.consent_publication }}
      </p>
    </div>
    <div>
      <label class="consent-fields__option">
        <input v-model="choice.age" type="checkbox" />
        <span>{{ AGE_CONFIRMATION_TEXT }}</span>
      </label>
      <p v-if="errors.consent_age" class="consent-fields__error">
        {{ errors.consent_age }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.consent-fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.consent-fields__option {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  font-size: var(--font-size-label);
  cursor: pointer;
}

.consent-fields__option input {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  margin: 0;
  accent-color: var(--color-primary);
}

.consent-fields__error {
  margin-top: var(--space-1);
  padding-left: calc(20px + var(--space-3));
  color: var(--color-danger);
  font-size: var(--font-size-label);
}
</style>
