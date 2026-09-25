<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useUserStore } from '@/entities/user'
import { SITE_NAME } from '@/shared/config'
import { AppButton } from '@/shared/ui'

// Шапка лендинга и страницы клубов: вместо вкладок приложения — название
// сервиса и «Войти», а вошедшему — ссылка на профиль.
const route = useRoute()
const userStore = useUserStore()
</script>

<template>
  <header class="landing-header">
    <div class="landing-header__inner">
      <RouterLink :to="{ name: 'home' }" class="landing-header__brand">
        {{ SITE_NAME }}
        <span class="landing-header__beta">Бета</span>
      </RouterLink>
      <AppButton v-if="userStore.user" variant="secondary" :to="{ name: 'profile' }">
        Профиль
      </AppButton>
      <AppButton
        v-else
        variant="secondary"
        :to="{ name: 'login', query: { redirect: route.fullPath } }"
      >
        Войти
      </AppButton>
    </div>
  </header>
</template>

<style scoped>
.landing-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.landing-header__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  max-width: var(--content-max-width);
  height: 56px;
  margin: 0 auto;
  padding: 0 var(--page-padding);
}

.landing-header__brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: var(--font-weight-heading);
  text-decoration: none;
}

.landing-header__beta {
  padding: 2px var(--space-2);
  background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface));
  border-radius: var(--radius-badge);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: var(--font-weight-label);
}

@media (min-width: 768px) {
  .landing-header__inner {
    height: 64px;
  }
}
</style>
