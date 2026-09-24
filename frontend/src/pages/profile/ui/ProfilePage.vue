<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useUserStore } from '@/entities/user'
import { LogoutButton } from '@/features/auth'
import { AppCard, PageHeader } from '@/shared/ui'

// Пока только имя, смена пароля и выход; полный профиль — по макету profile_settings.
const router = useRouter()
const userStore = useUserStore()
</script>

<template>
  <main class="page page--narrow">
    <PageHeader title="Профиль" />
    <AppCard v-if="userStore.user" class="profile-page__card">
      <div>
        <p class="profile-page__name">{{ userStore.user.display_name }}</p>
        <p class="page__muted">{{ userStore.user.login }}</p>
      </div>
      <RouterLink :to="{ name: 'change-password' }">Сменить пароль</RouterLink>
    </AppCard>
    <LogoutButton @done="router.replace({ name: 'home' })" />
  </main>
</template>

<style scoped>
.profile-page__card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.profile-page__name {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}
</style>
