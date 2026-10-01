<script setup lang="ts">
import { ForgotPasswordForm } from '@/features/password-recovery'
import { AppCard, PageHeader } from '@/shared/ui'
</script>

<template>
  <main class="forgot-page">
    <PageHeader title="Восстановление пароля" :back-to="{ name: 'login' }" />
    <AppCard>
      <ForgotPasswordForm />
    </AppCard>
    <p class="forgot-page__note">
      Нет почты в аккаунте? Попросите организатора своего клуба сбросить пароль
    </p>
  </main>
</template>

<style scoped>
.forgot-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: 480px;
  margin: 0 auto;
  padding: var(--space-4) var(--page-padding) var(--space-6);
}

.forgot-page__note {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  text-align: center;
}
</style>
