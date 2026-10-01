<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { confirmEmail } from '@/features/email-bind'
import { ApiError } from '@/shared/api'
import { useLinkToken } from '@/shared/lib'
import { AppButton, AppCard, FormError, PageHeader } from '@/shared/ui'

// The link from the letter: /confirm-email#token=… (useLinkToken). Opens without logging in (often
// on a phone's mail app). The email is confirmed by a button, not on opening:
// mail services open links from letters by themselves to check them.
const userStore = useUserStore()
const token = useLinkToken()

const loading = ref(false)
const confirmed = ref<string | null>(null)
const error = ref(token ? '' : 'В ссылке нет кода подтверждения. Откройте ссылку из письма целиком')

async function confirm() {
  error.value = ''
  loading.value = true
  try {
    confirmed.value = await confirmEmail(token)
    // The same user in this browser: the settings show the new address right away.
    const user = userStore.user
    if (user?.pending_email?.address === confirmed.value) {
      userStore.setEmail({ email: confirmed.value, pending_email: null })
    }
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось подтвердить почту'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="page page--narrow">
    <PageHeader title="Подтверждение почты" />
    <AppCard class="email-confirm">
      <template v-if="confirmed">
        <p class="email-confirm__done">Почта {{ confirmed }} привязана к аккаунту</p>
        <AppButton v-if="userStore.user" :to="{ name: 'profile-settings' }" variant="secondary">
          К настройкам
        </AppButton>
        <AppButton v-else :to="{ name: 'login' }" variant="secondary">Войти</AppButton>
      </template>
      <template v-else>
        <p v-if="token">Нажмите кнопку, чтобы привязать почту к аккаунту</p>
        <FormError v-if="error" :message="error" />
        <AppButton v-if="token" :loading="loading" @click="confirm">Подтвердить почту</AppButton>
      </template>
    </AppCard>
  </main>
</template>

<style scoped>
.email-confirm {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.email-confirm__done {
  color: var(--color-personal-best);
  font-weight: var(--font-weight-label);
  overflow-wrap: anywhere;
}
</style>
