<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { onMounted, ref } from 'vue'
import { UserRow } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { formatDate } from '@/shared/lib'
import { AppCard, AppInput } from '@/shared/ui'
import { searchDeletedUsers, type DeletedUser } from '../api/deletedNamesApi'
import AnonymizeButton from './AnonymizeButton.vue'

// Deleted accounts that kept their name in results and records, and withdrawing that
// consent at the person's request: the name is replaced with the deleted-user name.
const query = ref('')
const users = ref<DeletedUser[] | null>(null)
const loadError = ref('')

async function load() {
  try {
    users.value = await searchDeletedUsers(query.value.trim())
    loadError.value = ''
  } catch (e) {
    loadError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить список'
  }
}

onMounted(load)
watchDebounced(query, load, { debounce: 300 })
</script>

<template>
  <AppCard class="deleted-names">
    <p class="deleted-names__muted">
      Эти люди удалили аккаунт, но оставили имя в таблицах результатов и рекордов.
      Если человек отзывает согласие, обезличьте его.
    </p>
    <AppInput v-model="query" label="Имя" autocomplete="off" />

    <p v-if="loadError" class="deleted-names__error" role="alert">{{ loadError }}</p>
    <p v-else-if="users && users.length === 0" class="deleted-names__muted">Никого не нашлось</p>
    <ul v-else-if="users" class="deleted-names__list">
      <li v-for="user in users" :key="user.id">
        <UserRow
          :display-name="user.display_name"
          :details="`удалён ${formatDate(user.deleted_at.slice(0, 10))}`"
        >
          <AnonymizeButton :user="user" @anonymized="load" />
        </UserRow>
      </li>
    </ul>
  </AppCard>
</template>

<style scoped>
.deleted-names {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.deleted-names__muted {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.deleted-names__error {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}

.deleted-names__list {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.deleted-names__list li + li {
  border-top: 1px solid var(--color-border);
}
</style>
