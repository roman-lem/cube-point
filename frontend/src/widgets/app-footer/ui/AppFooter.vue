<script setup lang="ts">
// Строка про бету — в подвале лендинга и страницы клубов.
defineProps<{ betaNote?: boolean }>()
</script>

<template>
  <footer class="app-footer">
    <p v-if="betaNote" class="app-footer__note">
      Сервис в бета-версии — если что-то работает не так, свяжитесь с разработчиком
    </p>
    <div class="app-footer__links">
      <RouterLink :to="{ name: 'privacy' }">Политика обработки персональных данных</RouterLink>
      <RouterLink :to="{ name: 'publication-consent' }">
        Согласие на распространение персональных данных
      </RouterLink>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  /* Внизу страницы, но перед местом под нижнюю навигацию (order: 99). */
  order: 98;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: auto;
  padding: var(--space-4) var(--page-padding) var(--space-5);
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  text-align: center;
}

.app-footer__links {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-1) var(--space-4);
}

.app-footer a {
  color: var(--color-text-secondary);
}
</style>
