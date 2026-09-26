<script setup lang="ts">
import { computed, ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { AppButton, AppInput, ConfirmDialog, SettingRow } from '@/shared/ui'
import { deleteAccount } from '../api/deleteAccount'

// Deleting one's own account, confirmed with the password. Login, email, password
// and consents are destroyed, results stay under the deleted-user name.
// The "keep my name" checkbox keeps the name in result and record tables:
// the given publication consent is not withdrawn, and there is no profile anymore.
// The checkbox is absent if there are no current-version consents (the /consent page).
// The last organizer of a club has to hand over the role first (restriction from the server).
const emit = defineEmits<{ deleted: [] }>()

const userStore = useUserStore()
const open = ref(false)
const password = ref('')
const keepName = ref(false)
const passwordError = ref('')
const error = ref('')
const loading = ref(false)

const canKeepName = computed(() => userStore.user?.consents_required === false)
const resultsName = computed(() =>
  keepName.value ? `под именем «${userStore.user?.display_name}»` : 'под именем «Удалённый участник»',
)

function openDialog() {
  password.value = ''
  keepName.value = false
  passwordError.value = ''
  error.value = ''
  open.value = true
}

async function submit() {
  passwordError.value = ''
  error.value = ''
  if (!password.value) {
    passwordError.value = 'Введите пароль'
    return
  }
  loading.value = true
  try {
    await deleteAccount(password.value, canKeepName.value && keepName.value)
    open.value = false
    userStore.clear()
    emit('deleted')
  } catch (e) {
    if (e instanceof ApiError && e.fields.password) {
      passwordError.value = e.fields.password
    } else if (e instanceof ApiError && e.fields.keep_name) {
      error.value = e.fields.keep_name
    } else {
      error.value = e instanceof ApiError ? e.message : 'Не удалось удалить аккаунт'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <SettingRow
    title="Удалить аккаунт"
    description="Логин, пароль, почта и согласия будут удалены. Результаты и рекорды останутся под именем «Удалённый участник» или, если захотите, под вашим именем."
    :restriction="userStore.user?.delete_restriction"
  >
    <AppButton
      variant="danger"
      :disabled="Boolean(userStore.user?.delete_restriction)"
      @click="openDialog"
    >
      Удалить аккаунт
    </AppButton>
  </SettingRow>

  <ConfirmDialog
    v-model:open="open"
    title="Удалить аккаунт?"
    confirm-label="Удалить навсегда"
    danger
    :loading="loading"
    @confirm="submit"
  >
    <form class="delete-account__form" @submit.prevent="submit">
      <p>
        Восстановить аккаунт будет нельзя. Вы выйдете из всех клубов и на всех устройствах.
        Результаты встреч и рекорды останутся в таблицах {{ resultsName }}.
      </p>
      <div v-if="canKeepName">
        <label class="delete-account__option">
          <input v-model="keepName" type="checkbox" />
          <span>Оставить моё имя в результатах и рекордах клубов</span>
        </label>
        <p class="delete-account__hint">
          Имя останется в таблицах результатов и рекордов. Всё остальное — логин, почта,
          пароль — будет удалено. Отозвать это согласие можно, написав разработчику
        </p>
      </div>
      <AppInput
        v-model="password"
        label="Пароль"
        type="password"
        autocomplete="current-password"
        :error="passwordError"
      />
      <p v-if="error" class="delete-account__error" role="alert">{{ error }}</p>
    </form>
  </ConfirmDialog>
</template>

<style scoped>
.delete-account__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  color: var(--color-text-primary);
}

.delete-account__option {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  cursor: pointer;
}

.delete-account__option input {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  margin: 0;
  accent-color: var(--color-primary);
}

.delete-account__hint {
  margin-top: var(--space-1);
  padding-left: calc(20px + var(--space-3));
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.delete-account__error {
  color: var(--color-danger);
}
</style>
