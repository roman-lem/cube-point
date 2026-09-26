<script setup lang="ts">
import { ref } from 'vue'
import { AppButton, AppIcon, TemporaryPassword } from '@/shared/ui'
import { createClubMember, type AddedParticipant } from '../api/participantsApi'
import NewcomerForm from './NewcomerForm.vue'

// An account for a newcomer from the club member list: in the club right away, with a temporary password.
const { clubId } = defineProps<{ clubId: number }>()
const emit = defineEmits<{ created: [userId: number] }>()

const dialog = ref<HTMLDialogElement>()
const created = ref<AddedParticipant | null>(null)
// A new form on every open, so no fields and errors are left over from last time.
const formKey = ref(0)

function open() {
  created.value = null
  formKey.value++
  dialog.value?.showModal()
}

function close() {
  dialog.value?.close()
}

const create = (displayName: string, login: string) => createClubMember(clubId, displayName, login)

function onCreated(result: AddedParticipant) {
  created.value = result
  emit('created', result.user.id)
}
</script>

<template>
  <AppButton variant="secondary" @click="open">
    <AppIcon name="person-add" :size="20" />
    Создать аккаунт
  </AppButton>

  <dialog ref="dialog" class="create-member" @click.self="close">
    <div class="create-member__body">
      <h2 class="create-member__title">Аккаунт для новичка</h2>

      <template v-if="created">
        <p>
          Аккаунт создан, «{{ created.user.display_name }}» теперь в клубе.
          Передайте логин и временный пароль — <strong>пароль показывается один раз</strong>.
          При первом входе его нужно будет сменить.
        </p>
        <TemporaryPassword :login="created.user.login" :password="created.temporary_password!" />
        <AppButton @click="close">Готово</AppButton>
      </template>

      <template v-else>
        <p class="create-member__muted">
          Для тех, кто пришёл без телефона: организатор вводит результаты за него,
          а войти он сможет позже по временному паролю.
        </p>
        <NewcomerForm :key="formKey" :create="create" submit-label="Создать" @created="onCreated" />
        <AppButton variant="secondary" @click="close">Закрыть</AppButton>
      </template>
    </div>
  </dialog>
</template>

<style scoped>
.create-member {
  width: calc(100% - 2 * var(--page-padding));
  max-width: 480px;
  padding: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: inherit;
}

.create-member::backdrop {
  background: color-mix(in srgb, var(--color-text-primary) 40%, transparent);
}

.create-member__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-4) var(--space-4);
}

.create-member__title {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.create-member__muted {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}
</style>
