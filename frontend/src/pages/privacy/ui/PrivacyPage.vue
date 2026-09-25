<script setup lang="ts">
import { CONSENT_VERSIONS } from '@/features/auth'
import { PageHeader } from '@/shared/ui'

// Политика обработки персональных данных и тексты обоих согласий.
// Чекбоксы регистрации ведут на #processing и #publication.
// При изменении текста согласия меняется его версия в CONSENT_VERSIONS
// (features/auth/model/consents.ts) и в backend/app/consents.py.
//
// ЗАГЛУШКА: текст ниже — черновик-заполнитель, его заменит владелец проекта.
</script>

<template>
  <main class="page page--narrow privacy">
    <PageHeader title="Политика обработки персональных данных" :back-to="{ name: 'home' }" />

    <p class="privacy__draft">Черновик: текст будет заменён окончательной редакцией.</p>

    <section class="page__section">
      <h2 class="page__section-title">1. Общие положения</h2>
      <p>
        Политика описывает, какие персональные данные обрабатывает сервис клубных встреч
        спидкуберов (далее — Сервис), зачем и как они защищены. Оператор персональных данных —
        [ФИО оператора], контакт для обращений — [адрес электронной почты].
      </p>
    </section>

    <section class="page__section">
      <h2 class="page__section-title">2. Какие данные мы обрабатываем</h2>
      <ul>
        <li>Отображаемое имя или никнейм — его вы выбираете сами.</li>
        <li>Логин и пароль (пароль хранится только в виде хеша).</li>
        <li>Адрес электронной почты, если вы его укажете.</li>
        <li>Результаты попыток на встречах клуба и решения FMC.</li>
        <li>Технические данные: cookie сессии, время входа.</li>
      </ul>
    </section>

    <section class="page__section">
      <h2 class="page__section-title">3. Цели обработки</h2>
      <p>
        Проведение клубных встреч, подсчёт результатов, ведение рекордов клуба и личной
        статистики, вход в аккаунт. [Уточнить цели и правовые основания.]
      </p>
    </section>

    <section class="page__section">
      <h2 class="page__section-title">4. Хранение и защита</h2>
      <p>
        Данные хранятся на сервере в [страна, город]. Сервис не загружает ресурсы со сторонних
        доменов и не использует внешнюю аналитику. [Сроки хранения, меры защиты.]
      </p>
    </section>

    <section class="page__section">
      <h2 class="page__section-title">5. Ваши права и удаление аккаунта</h2>
      <p>
        Вы можете отозвать согласие и удалить аккаунт в настройках профиля. При удалении
        логин, пароль, почта и согласия уничтожаются, а результаты остаются в таблицах под
        именем «Удалённый участник» и больше не связаны с вами. [Порядок обращений к оператору.]
      </p>
    </section>

    <section id="processing" class="page__section">
      <h2 class="page__section-title">Согласие на обработку персональных данных</h2>
      <p class="privacy__version">Редакция {{ CONSENT_VERSIONS.processing }}</p>
      <p>
        Я даю согласие [ФИО оператора] на обработку моих персональных данных, перечисленных
        в разделе 2, в целях, указанных в разделе 3, до удаления аккаунта или отзыва согласия.
        [Полный текст согласия.]
      </p>
    </section>

    <section id="publication" class="page__section">
      <h2 class="page__section-title">Согласие на распространение персональных данных</h2>
      <p class="privacy__version">Редакция {{ CONSENT_VERSIONS.publication }}</p>
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
.privacy ul {
  margin: 0;
  padding-left: var(--space-5);
}

.privacy section {
  /* Якоря #processing и #publication не прячутся под верхней навигацией. */
  scroll-margin-top: 80px;
}

.privacy__draft {
  padding: var(--space-3);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-button);
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.privacy__version {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}
</style>
