<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { checkPasswordReset, ResetPasswordForm } from '@/features/password-recovery'
import { ApiError } from '@/shared/api'
import { useLinkToken } from '@/shared/lib'
import { AppButton, AppCard, FormError, PageHeader } from '@/shared/ui'

// The link from the letter: /reset-password#token=… (useLinkToken). Opens without logging in.
// Opening the page only checks the link: mail services open links from letters
// by themselves, and the link is spent only by saving the new password.
const router = useRouter()
const token = useLinkToken()

const login = ref<string | null>(null)
const error = ref(token ? '' : 'В ссылке нет кода. Откройте ссылку из письма целиком')

onMounted(async () => {
  if (!token) {
    return
  }
  try {
    login.value = await checkPasswordReset(token)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось проверить ссылку'
  }
})

function onSuccess() {
  router.replace({ name: 'home' })
}
</script>

<template>
  <main class="reset-page">
    <PageHeader title="Новый пароль" />
    <AppCard class="reset-page__card">
      <template v-if="login">
        <p>Аккаунт: <b>@{{ login }}</b></p>
        <ResetPasswordForm :token="token" :login="login" @success="onSuccess" />
      </template>
      <template v-else-if="error">
        <FormError :message="error" />
        <AppButton :to="{ name: 'forgot-password' }" variant="secondary">Запросить новую ссылку</AppButton>
      </template>
    </AppCard>
    <p class="reset-page__note">После смены пароля вход на других устройствах будет сброшен</p>
  </main>
</template>

<style scoped>
.reset-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: 480px;
  margin: 0 auto;
  padding: var(--space-4) var(--page-padding) var(--space-6);
}

.reset-page__card {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.reset-page__note {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  text-align: center;
}
</style>
