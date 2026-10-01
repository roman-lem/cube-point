<script setup lang="ts">
import { computed, ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { useFormErrors } from '@/shared/lib'
import { AppButton, AppInput, ConfirmDialog, FormError } from '@/shared/ui'
import { changeDisplayName } from '../api/displayNameApi'

// The display name in the profile settings. It can be changed once in 30 days;
// the new name shows everywhere, past results and records too.
const userStore = useUserStore()
const name = computed(() => userStore.user?.display_name ?? '')
const availableAt = computed(() => userStore.user?.display_name_change_available_at ?? null)

const availableDate = computed(() => {
  if (!availableAt.value) {
    return ''
  }
  const date = new Date(availableAt.value)
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: date.getFullYear() === new Date().getFullYear() ? undefined : 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
})

const { fieldErrors, formError, clearErrors, showError } = useFormErrors()
const editing = ref(false)
const newName = ref('')
const confirmOpen = ref(false)
const loading = ref(false)
const changed = ref(false)

function startEditing() {
  clearErrors()
  changed.value = false
  newName.value = name.value
  editing.value = true
}

function submit() {
  clearErrors()
  const value = newName.value.trim()
  if (!value) {
    fieldErrors.value = { display_name: 'Введите имя или никнейм' }
    return
  }
  if (value === name.value) {
    fieldErrors.value = { display_name: 'Это ваше текущее имя' }
    return
  }
  confirmOpen.value = true
}

async function confirm() {
  loading.value = true
  try {
    userStore.setUser(await changeDisplayName(newName.value))
    editing.value = false
    changed.value = true
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
    confirmOpen.value = false
  }
}
</script>

<template>
  <div class="name-settings">
    <template v-if="!editing">
      <span>{{ name }}</span>
      <span class="name-settings__hint">Так вас видят в таблицах результатов</span>
      <p v-if="changed" class="name-settings__done">Имя изменено</p>
      <span v-if="availableAt" class="name-settings__hint">
        Имя можно менять раз в 30 дней. Следующая смена — {{ availableDate }}
      </span>
      <AppButton v-else variant="secondary" class="name-settings__button" @click="startEditing">
        Изменить имя
      </AppButton>
    </template>

    <form v-else class="name-settings__form" novalidate @submit.prevent="submit">
      <AppInput
        v-model="newName"
        label="Новое имя или никнейм"
        autocomplete="nickname"
        hint="Имя можно менять раз в 30 дней"
        :error="fieldErrors.display_name"
      />
      <div class="name-settings__actions">
        <AppButton type="submit">Сохранить</AppButton>
        <AppButton variant="secondary" @click="editing = false">Отмена</AppButton>
      </div>
    </form>
    <FormError v-if="formError" :message="formError" />
  </div>

  <ConfirmDialog
    v-model:open="confirmOpen"
    title="Сменить имя?"
    confirm-label="Сменить имя"
    :loading="loading"
    @confirm="confirm"
  >
    <p>
      Новое имя «{{ newName.trim() }}» появится во всех таблицах, в том числе в прошлых результатах
      и рекордах. Следующий раз сменить имя можно будет через 30 дней.
    </p>
  </ConfirmDialog>
</template>

<style scoped>
.name-settings {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.name-settings__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.name-settings__hint {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.name-settings__button {
  align-self: flex-start;
  margin-top: var(--space-2);
}

.name-settings__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.name-settings__done {
  color: var(--color-personal-best);
  font-weight: var(--font-weight-label);
}
</style>
