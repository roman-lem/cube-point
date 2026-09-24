<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/entities/user'
import { ChangePasswordForm, LogoutButton } from '@/features/auth'
import { safeRedirect } from '@/shared/lib'
import { AppCard, PageHeader } from '@/shared/ui'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// Вошли по временному паролю: пока его не сменить, в приложение не пускаем.
const forced = computed(() => userStore.user?.must_change_password ?? false)

function onSuccess() {
  router.replace(safeRedirect(route.query.redirect))
}

function onLogout() {
  router.replace({ name: 'login' })
}
</script>

<template>
  <main class="change-password-page">
    <PageHeader
      title="Смена пароля"
      :subtitle="forced ? 'Вы вошли по временному паролю. Придумайте новый, чтобы продолжить' : undefined"
      :back-to="forced ? undefined : { name: 'profile' }"
    />
    <AppCard>
      <ChangePasswordForm @success="onSuccess" />
    </AppCard>
    <p class="change-password-page__note">
      После смены пароля вход на других устройствах будет сброшен
    </p>
    <LogoutButton v-if="forced" @done="onLogout" />
  </main>
</template>

<style scoped>
.change-password-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: 480px;
  margin: 0 auto;
  padding: var(--space-4) var(--page-padding) var(--space-6);
}

.change-password-page__note {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  text-align: center;
}
</style>
