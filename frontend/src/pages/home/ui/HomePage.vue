<script setup lang="ts">
// Временная стартовая страница, пока нет страницы клуба.
import { useUserStore } from '@/entities/user'
import { LogoutButton } from '@/features/auth'
import { AppCard, PageHeader } from '@/shared/ui'

const userStore = useUserStore()
</script>

<template>
  <main class="home-page">
    <PageHeader title="Клуб" />
    <AppCard>
      <div v-if="userStore.user" class="home-page__card">
        <p>
          Вы вошли как <strong>{{ userStore.user.display_name }}</strong>
          ({{ userStore.user.login }})
        </p>
        <RouterLink :to="{ name: 'change-password' }">Сменить пароль</RouterLink>
        <LogoutButton />
      </div>
      <p v-else>
        <RouterLink :to="{ name: 'login' }">Войдите</RouterLink>
        или
        <RouterLink :to="{ name: 'register' }">зарегистрируйтесь</RouterLink>
      </p>
    </AppCard>
  </main>
</template>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: var(--space-4) var(--page-padding) var(--space-6);
}

.home-page__card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-3);
}
</style>
