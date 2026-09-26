<script setup lang="ts">
import { CONSENT_VERSIONS } from '@/features/auth'
import { DEVELOPER_CONTACTS, SITE_NAME } from '@/shared/config'
import { PageHeader } from '@/shared/ui'

// Consent to publication of personal data, as a separate document
// as required by Art. 10.1 of 152-FZ. The second registration checkbox links to it.
// When the text changes, the version CONSENT_VERSIONS.publication changes
// (features/auth/model/consents.ts) and in backend/app/consents.py.

// The site address is not written in the code: it is the address the page is opened at.
const siteAddress = window.location.origin
</script>

<template>
  <main class="page page--narrow publication-consent">
    <PageHeader
      title="Согласие на распространение персональных данных"
      :back-to="{ name: 'home' }"
    />

    <section class="page__section">
      <p class="publication-consent__version">Редакция {{ CONSENT_VERSIONS.publication }}</p>
      <p>
        В соответствии со статьёй 10.1 Федерального закона от 27.07.2006 № 152-ФЗ «О персональных данных» я, пользователь сайта «{{ SITE_NAME }}» с учётной записью, от имени которой даётся это согласие, даю согласие на распространение моих персональных данных на следующих условиях.
      </p>
      <p>
        <strong>Оператор:</strong> Лепарский Роман Денисович, контакт для обращений: {{ DEVELOPER_CONTACTS.email }}.
      </p>
      <p>
        <strong>Информационный ресурс, на котором осуществляется распространение:</strong> {{ siteAddress }}
      </p>
      <p>
        <strong>Цель распространения:</strong> публикация таблиц результатов клубных встреч, рекордов клубов и профилей участников.
      </p>
      <p>
        <strong>Персональные данные, разрешённые для распространения:</strong> отображаемое имя; результаты попыток и рекорды; сведения об участии во встречах; сведения о членстве в клубах.
      </p>
      <p>
        <strong>Персональные данные, не разрешённые для распространения:</strong> логин, адрес электронной почты, технические данные.
      </p>
      <p>
        <strong>Условия и запреты:</strong> запретов на обработку опубликованных данных неограниченным кругом лиц не устанавливаю.
      </p>
      <p>
        <strong>Срок действия согласия:</strong> до удаления моей учётной записи или до отзыва согласия. Если при удалении учётной записи я выберу сохранить своё отображаемое имя в таблицах результатов и рекордов клубов, согласие в части отображаемого имени и результатов действует до его отзыва.
      </p>
      <p>
        <strong>Отзыв согласия:</strong> я могу в любой момент потребовать прекратить распространение, направив требование на адрес {{ DEVELOPER_CONTACTS.email }}. Распространение прекращается в течение трёх рабочих дней с момента получения требования.
      </p>
    </section>
  </main>
</template>

<style scoped>
.publication-consent__version {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}
</style>
