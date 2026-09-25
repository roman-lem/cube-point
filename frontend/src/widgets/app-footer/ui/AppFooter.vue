<template>
  <footer class="app-footer">
    <RouterLink :to="{ name: 'privacy' }">Политика обработки персональных данных</RouterLink>
  </footer>
</template>

<style scoped>
.app-footer {
  /* Внизу страницы, но перед местом под нижнюю навигацию (order: 99). */
  order: 98;
  margin-top: auto;
  padding: var(--space-4) var(--page-padding) var(--space-5);
  font-size: var(--font-size-label);
  text-align: center;
}

.app-footer a {
  color: var(--color-text-secondary);
}
</style>
