<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { DeleteAccountControl } from '@/features/account-delete'
import { AcceptConsentsForm, LogoutButton } from '@/features/auth'
import { safeRedirect } from '@/shared/lib'
import { AppCard, PageHeader } from '@/shared/ui'

// Согласия от того, у кого их нет: аккаунт создал организатор или текст
// согласия обновился. Пока их не дать, приложение недоступно (guards.ts);
// не согласен — можно выйти или удалить аккаунт.
const route = useRoute()
const router = useRouter()
</script>

<template>
  <main class="page page--narrow">
    <PageHeader
      title="Согласие на обработку данных"
      subtitle="Чтобы продолжить, подтвердите согласие с политикой обработки персональных данных"
    />
    <AppCard>
      <AcceptConsentsForm @success="router.replace(safeRedirect(route.query.redirect))" />
    </AppCard>
    <AppCard>
      <DeleteAccountControl @deleted="router.replace({ name: 'home' })" />
    </AppCard>
    <LogoutButton @done="router.replace({ name: 'login' })" />
  </main>
</template>
