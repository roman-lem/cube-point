<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/entities/user'
import { DeleteAccountControl } from '@/features/account-delete'
import { ChangePasswordForm, LogoutButton } from '@/features/auth'
import { AppCard, AppIcon, PageHeader } from '@/shared/ui'

// One's own account settings. Name and login are read-only
// for now, there is no email binding yet.
const router = useRouter()
const userStore = useUserStore()
const passwordChanged = ref(false)
</script>

<template>
  <main class="page page--narrow">
    <PageHeader title="Настройки" :back-to="{ name: 'profile' }" />

    <template v-if="userStore.user">
      <section class="page__section">
        <h2 class="page__section-title">Профиль</h2>
        <AppCard class="settings__fields">
          <div class="settings__field">
            <span class="settings__label">Имя или никнейм</span>
            <span>{{ userStore.user.display_name }}</span>
            <span class="settings__hint">Так вас видят в таблицах результатов</span>
          </div>
          <div class="settings__field">
            <span class="settings__label">Логин</span>
            <span class="settings__login">
              {{ userStore.user.login }}
              <AppIcon name="lock" :size="16" />
            </span>
            <span class="settings__hint">Логин не меняется и виден только организаторам</span>
          </div>
        </AppCard>
      </section>

      <section class="page__section">
        <h2 class="page__section-title">Пароль</h2>
        <AppCard>
          <p v-if="passwordChanged" class="settings__done">Пароль изменён</p>
          <ChangePasswordForm v-else @success="passwordChanged = true" />
        </AppCard>
        <p class="settings__hint">После смены пароля вход на других устройствах будет сброшен</p>
      </section>

      <AppCard v-if="userStore.user.is_admin" class="settings__admin">
        <RouterLink :to="{ name: 'admin-clubs' }">Администрирование</RouterLink>
        <RouterLink :to="{ name: 'admin-users' }">Пользователи</RouterLink>
        <RouterLink :to="{ name: 'admin-deleted-users' }">Имена удалённых аккаунтов</RouterLink>
      </AppCard>

      <LogoutButton @done="router.replace({ name: 'home' })" />

      <section class="page__section">
        <h2 class="page__section-title">Удаление аккаунта</h2>
        <AppCard>
          <DeleteAccountControl @deleted="router.replace({ name: 'home' })" />
        </AppCard>
      </section>
    </template>
  </main>
</template>

<style scoped>
.settings__admin {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.settings__fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.settings__field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.settings__label {
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.settings__login {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-text-secondary);
}

.settings__hint {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.settings__done {
  color: var(--color-personal-best);
  font-weight: var(--font-weight-label);
}
</style>
