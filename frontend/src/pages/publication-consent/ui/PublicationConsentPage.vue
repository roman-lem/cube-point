<script setup lang="ts">
import { CONSENT_VERSIONS } from '@/features/auth'
import { PageHeader } from '@/shared/ui'

// Согласие на распространение персональных данных — отдельным документом,
// как требует ст. 10.1 ФЗ-152. На него ведёт второй чекбокс регистрации.
// При изменении текста меняется версия CONSENT_VERSIONS.publication
// (features/auth/model/consents.ts) и в backend/app/consents.py.
//
// ЗАГЛУШКА: текст ниже — черновик-заполнитель, его заменит владелец проекта.
</script>

<template>
  <main class="page page--narrow publication-consent">
    <PageHeader
      title="Согласие на распространение персональных данных"
      :back-to="{ name: 'home' }"
    />

    <p class="publication-consent__draft">
      Черновик: текст будет заменён окончательной редакцией.
    </p>

    <section class="page__section">
      <p class="publication-consent__version">Редакция {{ CONSENT_VERSIONS.publication }}</p>
      <p>
        Я даю согласие [ФИО оператора] на публикацию в открытом доступе на сайте [адрес сайта]
        моего отображаемого имени и результатов на встречах клуба: в таблицах результатов,
        рекордах клуба и в публичном профиле. Другие данные не публикуются. Согласие действует
        до удаления аккаунта или отзыва согласия. [Условия и запреты, полный текст согласия.]
      </p>
    </section>
  </main>
</template>

<style scoped>
.publication-consent__draft {
  padding: var(--space-3);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-button);
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.publication-consent__version {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}
</style>
