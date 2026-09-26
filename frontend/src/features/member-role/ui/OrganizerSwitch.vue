<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ClubMemberCard } from '@/entities/club'
import { useUserStore } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { ConfirmDialog, SettingRow } from '@/shared/ui'
import { makeOrganizer, removeOrganizer } from '../api/organizerApi'

// The "Club organizer" switch. A removed organizer stays a member,
// the last one cannot be removed. Removing one's own rights requires confirmation:
// after that one can no longer manage the club.
const { clubId, member } = defineProps<{ clubId: number; member: ClubMemberCard }>()
const emit = defineEmits<{ changed: [member: ClubMemberCard] }>()

const userStore = useUserStore()
const loading = ref(false)
const error = ref('')
const confirmSelfOpen = ref(false)

const isOrganizer = computed(() => member.role === 'organizer')
const isSelf = computed(() => userStore.user?.id === member.user.id)

async function save(organizer: boolean) {
  loading.value = true
  error.value = ''
  try {
    const action = organizer ? makeOrganizer : removeOrganizer
    emit('changed', await action(clubId, member.user.id))
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось изменить права'
  } finally {
    loading.value = false
    confirmSelfOpen.value = false
  }
}

function toggle() {
  if (isOrganizer.value && isSelf.value) {
    confirmSelfOpen.value = true
  } else {
    save(!isOrganizer.value)
  }
}
</script>

<template>
  <SettingRow
    title="Организатор клуба"
    description="Создаёт встречи, вносит результаты участников и управляет клубом."
    :restriction="member.restrictions.organizer"
  >
    <template #details>
      <p v-if="error" class="organizer-switch__error" role="alert">{{ error }}</p>
    </template>
    <button
      type="button"
      role="switch"
      :aria-checked="isOrganizer"
      aria-label="Организатор клуба"
      class="organizer-switch"
      :disabled="loading || member.restrictions.organizer !== null"
      @click="toggle"
    >
      <span class="organizer-switch__thumb" />
    </button>
  </SettingRow>

  <ConfirmDialog
    v-model:open="confirmSelfOpen"
    title="Снять права с себя?"
    confirm-label="Снять"
    danger
    :loading="loading"
    @confirm="save(false)"
  >
    <p>Вы останетесь участником клуба, но больше не сможете управлять им и встречами.</p>
  </ConfirmDialog>
</template>

<style scoped>
.organizer-switch {
  position: relative;
  flex-shrink: 0;
  width: 52px;
  height: 32px;
  padding: 0;
  background: var(--color-border);
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: background 0.15s;
}

.organizer-switch[aria-checked='true'] {
  background: var(--color-primary);
}

.organizer-switch:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.organizer-switch__thumb {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 24px;
  height: 24px;
  background: var(--color-surface);
  border-radius: 50%;
  transition: transform 0.15s;
}

.organizer-switch[aria-checked='true'] .organizer-switch__thumb {
  transform: translateX(20px);
}

.organizer-switch__error {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}
</style>
