<script setup lang="ts">
import { computed, ref } from 'vue'
import { useUserStore, type EmailState } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { useFormErrors } from '@/shared/lib'
import { AppButton, AppInput, ConfirmDialog, FormError } from '@/shared/ui'
import { cancelPendingEmail, removeEmail, requestEmail } from '../api/emailApi'

// The email in the profile settings. An address is bound only after the link
// from the letter is opened (the email-confirm page); until then it is pending,
// and a confirmed address stays the old one. A new address and removing need
// the password; sending the letter again to the pending address does not.
const userStore = useUserStore()
const email = computed(() => userStore.user?.email ?? null)
const pending = computed(() => userStore.user?.pending_email ?? null)

const { fieldErrors, formError, clearErrors, showError } = useFormErrors()
const address = ref('')
const addressPassword = ref('')
// The address form: always without an email, on "Change" otherwise.
const editing = ref(false)
const showForm = computed(() => editing.value || (!email.value && !pending.value))
const loading = ref(false)
const sent = ref(false)

function apply(state: EmailState) {
  userStore.setEmail(state)
  editing.value = false
  address.value = ''
  addressPassword.value = ''
}

function startEditing() {
  clearErrors()
  sent.value = false
  address.value = ''
  addressPassword.value = ''
  editing.value = true
}

async function run(action: () => Promise<EmailState>, letter: boolean) {
  clearErrors()
  sent.value = false
  loading.value = true
  try {
    apply(await action())
    sent.value = letter
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

function submit() {
  const errors: Record<string, string> = {}
  if (!address.value.trim()) errors.email = 'Введите адрес почты'
  if (!addressPassword.value) errors.password = 'Введите пароль'
  if (Object.keys(errors).length > 0) {
    fieldErrors.value = errors
    return
  }
  run(() => requestEmail(address.value, addressPassword.value), true)
}

// Removing: a dialog with the password.
const removeOpen = ref(false)
const password = ref('')
const passwordError = ref('')
const removeError = ref('')
const removing = ref(false)

function openRemove() {
  password.value = ''
  passwordError.value = ''
  removeError.value = ''
  removeOpen.value = true
}

async function confirmRemove() {
  passwordError.value = ''
  removeError.value = ''
  if (!password.value) {
    passwordError.value = 'Введите пароль'
    return
  }
  removing.value = true
  try {
    apply(await removeEmail(password.value))
    sent.value = false
    removeOpen.value = false
  } catch (e) {
    if (e instanceof ApiError && e.fields.password) {
      passwordError.value = e.fields.password
    } else {
      removeError.value = e instanceof ApiError ? e.message : 'Не удалось отвязать почту'
    }
  } finally {
    removing.value = false
  }
}
</script>

<template>
  <div class="email-settings">
    <div v-if="email" class="email-settings__block">
      <span class="email-settings__address">{{ email }}</span>
      <span class="email-settings__hint">Почта подтверждена</span>
      <div v-if="!editing" class="email-settings__actions">
        <AppButton variant="secondary" @click="startEditing">Изменить</AppButton>
        <AppButton variant="secondary" @click="openRemove">Отвязать</AppButton>
      </div>
    </div>

    <div v-if="pending" class="email-settings__block">
      <span class="email-settings__label">Ожидает подтверждения</span>
      <span class="email-settings__address">{{ pending.address }}</span>
      <span v-if="pending.expired" class="email-settings__hint">
        Ссылка в письме устарела. Отправьте письмо ещё раз
      </span>
      <span v-else class="email-settings__hint">
        Мы отправили письмо со ссылкой. Ссылка действует 24 часа.
        <template v-if="email">До подтверждения остаётся прежняя почта.</template>
      </span>
      <p v-if="sent" class="email-settings__done">Письмо отправлено</p>
      <div v-if="!editing" class="email-settings__actions">
        <AppButton
          variant="secondary"
          :loading="loading"
          @click="run(() => requestEmail(pending!.address), true)"
        >
          Отправить ещё раз
        </AppButton>
        <AppButton variant="secondary" @click="startEditing">Изменить адрес</AppButton>
        <AppButton variant="secondary" @click="run(cancelPendingEmail, false)">Отменить</AppButton>
      </div>
    </div>

    <form v-if="showForm" class="email-settings__form" novalidate @submit.prevent="submit">
      <AppInput
        v-model="address"
        :label="email || pending ? 'Новый адрес почты' : 'Адрес почты'"
        type="email"
        autocomplete="email"
        hint="Придёт письмо со ссылкой для подтверждения. Почту видите только вы"
        :error="fieldErrors.email"
      />
      <AppInput
        v-model="addressPassword"
        label="Текущий пароль"
        type="password"
        autocomplete="current-password"
        :error="fieldErrors.password"
      />
      <div class="email-settings__actions">
        <AppButton type="submit" :loading="loading">Отправить письмо</AppButton>
        <AppButton v-if="editing" variant="secondary" @click="editing = false">Отмена</AppButton>
      </div>
    </form>

    <FormError v-if="formError" :message="formError" />
  </div>

  <ConfirmDialog
    v-model:open="removeOpen"
    title="Отвязать почту?"
    confirm-label="Отвязать"
    danger
    :loading="removing"
    @confirm="confirmRemove"
  >
    <form class="email-settings__form" @submit.prevent="confirmRemove">
      <p>Адрес {{ email }} будет удалён из аккаунта. Привязать почту можно будет снова.</p>
      <AppInput
        v-model="password"
        label="Пароль"
        type="password"
        autocomplete="current-password"
        :error="passwordError"
      />
      <FormError v-if="removeError" :message="removeError" />
    </form>
  </ConfirmDialog>
</template>

<style scoped>
.email-settings,
.email-settings__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.email-settings__block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.email-settings__label {
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.email-settings__address {
  overflow-wrap: anywhere;
}

.email-settings__hint {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.email-settings__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.email-settings__done {
  color: var(--color-personal-best);
  font-weight: var(--font-weight-label);
}
</style>
