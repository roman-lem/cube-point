<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LoginForm, RegisterForm } from '@/features/auth'
import { safeRedirect } from '@/shared/lib'
import { AppCard, PageHeader } from '@/shared/ui'

// Одна страница на два маршрута: /login и /register.
const route = useRoute()
const router = useRouter()

const isLogin = computed(() => route.name === 'login')
// ?redirect=… переносится при переключении между входом и регистрацией.
const switchTo = computed(() => ({
  name: isLogin.value ? 'register' : 'login',
  query: route.query,
}))

function onSuccess() {
  router.replace(safeRedirect(route.query.redirect))
}
</script>

<template>
  <main class="auth-page">
    <PageHeader :title="isLogin ? 'Вход' : 'Регистрация'" :back-to="{ name: 'home' }" />
    <AppCard>
      <LoginForm v-if="isLogin" @success="onSuccess" />
      <RegisterForm v-else @success="onSuccess" />
    </AppCard>
    <p class="auth-page__switch">
      <template v-if="isLogin">
        Нет аккаунта? <RouterLink :to="switchTo">Зарегистрироваться</RouterLink>
      </template>
      <template v-else>
        Уже есть аккаунт? <RouterLink :to="switchTo">Войти</RouterLink>
      </template>
    </p>
    <p v-if="!isLogin" class="auth-page__note">
      Почту для восстановления пароля можно будет привязать в личном кабинете
    </p>
  </main>
</template>

<style scoped>
.auth-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: 480px;
  margin: 0 auto;
  padding: var(--space-4) var(--page-padding) var(--space-6);
}

.auth-page__switch,
.auth-page__note {
  color: var(--color-text-secondary);
  text-align: center;
}

.auth-page__switch a {
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.auth-page__note {
  margin-top: calc(-1 * var(--space-3));
  font-size: var(--font-size-label);
}
</style>
