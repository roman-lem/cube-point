<script setup lang="ts">
import { ref } from 'vue'
import { ApiError } from '@/shared/api'
import { ConfirmDialog } from '@/shared/ui'
import { anonymizeDeletedUser } from '../api/deletedNamesApi'

// Withdrawing the name consent of a deleted account that kept its name:
// the name is replaced with the deleted-user name. Used in the list of such
// accounts and in the administrator's user card.
const { user } = defineProps<{ user: { id: number; display_name: string } }>()
const emit = defineEmits<{ anonymized: [] }>()

const open = ref(false)
const busy = ref(false)
const error = ref('')

function ask() {
  error.value = ''
  open.value = true
}

async function anonymize() {
  busy.value = true
  error.value = ''
  try {
    await anonymizeDeletedUser(user.id)
    open.value = false
    emit('anonymized')
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось обезличить'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <button type="button" class="anonymize" @click="ask">Обезличить</button>

  <ConfirmDialog
    v-model:open="open"
    title="Обезличить участника?"
    confirm-label="Обезличить"
    danger
    :loading="busy"
    @confirm="anonymize"
  >
    <p>
      Имя «{{ user.display_name }}» будет заменено на «Удалённый участник» во всех таблицах
      результатов и рекордах, запись о согласии удалится. Отменить это нельзя.
    </p>
    <p v-if="error" class="anonymize__error" role="alert">{{ error }}</p>
  </ConfirmDialog>
</template>

<style scoped>
.anonymize {
  flex-shrink: 0;
  min-height: var(--control-height);
  padding: 0 var(--space-3);
  background: none;
  border: none;
  border-radius: var(--radius-button);
  color: var(--color-danger);
  font: inherit;
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.anonymize__error {
  color: var(--color-danger);
}
</style>
