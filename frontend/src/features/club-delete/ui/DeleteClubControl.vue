<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AdminClub } from '@/entities/club'
import { ApiError } from '@/shared/api'
import { plural } from '@/shared/lib'
import { AppButton, AppCard, AppInput, ConfirmDialog, SettingRow } from '@/shared/ui'
import { deleteClub } from '../api/deleteClub'

// Deleting a club by the administrator: meetups, results, records, links and
// memberships go, the accounts stay. The club name has to be typed in to confirm
// (the server checks it too). Not possible while a meetup is live (restriction from the server).
const { club } = defineProps<{ club: AdminClub }>()
const emit = defineEmits<{ deleted: [] }>()

const open = ref(false)
const name = ref('')
const nameError = ref('')
const error = ref('')
const loading = ref(false)

// Names are saved without extra spaces, so only the edges are trimmed, as on the server.
const nameMatches = computed(() => name.value.trim() === club.name)

function openDialog() {
  name.value = ''
  nameError.value = ''
  error.value = ''
  open.value = true
}

async function submit() {
  if (!nameMatches.value) {
    return
  }
  nameError.value = ''
  error.value = ''
  loading.value = true
  try {
    await deleteClub(club.id, name.value)
    open.value = false
    emit('deleted')
  } catch (e) {
    if (e instanceof ApiError && e.fields.name) {
      nameError.value = e.fields.name
    } else {
      error.value = e instanceof ApiError ? e.message : 'Не удалось удалить клуб'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AppCard class="delete-club">
    <h2 class="delete-club__heading">Опасная зона</h2>
    <SettingRow
      title="Удалить клуб"
      description="Встречи, результаты, рекорды клуба и ссылки будут удалены. Аккаунты участников останутся."
      :restriction="club.delete_restriction"
    >
      <AppButton variant="danger" :disabled="Boolean(club.delete_restriction)" @click="openDialog">
        Удалить клуб
      </AppButton>
    </SettingRow>
  </AppCard>

  <ConfirmDialog
    v-model:open="open"
    title="Удалить клуб?"
    confirm-label="Удалить навсегда"
    danger
    :loading="loading"
    :confirm-disabled="!nameMatches"
    @confirm="submit"
  >
    <form class="delete-club__form" novalidate @submit.prevent="submit">
      <p>Восстановить клуб будет нельзя. Вместе с ним удалятся:</p>
      <ul class="delete-club__list">
        <li>{{ plural(club.deletion.meetups, ['встреча', 'встречи', 'встреч']) }} со скрамблами и заявками;</li>
        <li>
          {{ plural(club.deletion.results, ['результат', 'результата', 'результатов']) }}
          с историей правок, дисквалификации и рекорды клуба;
        </li>
        <li>
          членство {{ plural(club.deletion.members, ['участника', 'участников', 'участников']) }}
          в клубе и ссылки клуба.
        </li>
      </ul>
      <p>
        Аккаунты участников останутся, их личные рекорды пересчитаются по результатам в других
        клубах.
      </p>
      <AppInput
        v-model="name"
        :label="`Введите название клуба: ${club.name}`"
        autocomplete="off"
        :error="nameError"
      />
      <p v-if="error" class="delete-club__error" role="alert">{{ error }}</p>
    </form>
  </ConfirmDialog>
</template>

<style scoped>
.delete-club {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.delete-club__heading {
  color: var(--color-danger);
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.delete-club__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  color: var(--color-text-primary);
}

.delete-club__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding-left: var(--space-5);
  list-style: disc;
}

.delete-club__error {
  color: var(--color-danger);
}
</style>
