<script setup lang="ts">
import type { NameChange } from '../model/types'

// The history of a user's display name: for the administrator and the organizers
// of the user's clubs. The date is in the viewer's own time zone.
defineProps<{ history: NameChange[] }>()

const dateFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
</script>

<template>
  <p v-if="history.length === 0" class="name-history__empty">Имя не менялось.</p>
  <ul v-else class="name-history">
    <li v-for="(change, index) in history" :key="index" class="name-history__item">
      <span class="name-history__names">{{ change.old_name }} → {{ change.new_name }}</span>
      <span class="name-history__meta">
        {{ dateFormat.format(new Date(change.changed_at)) }}
        <template v-if="change.by_admin">, вернул администратор</template>
      </span>
    </li>
  </ul>
</template>

<style scoped>
.name-history {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.name-history__item {
  display: flex;
  flex-direction: column;
}

.name-history__names {
  overflow-wrap: anywhere;
}

.name-history__meta,
.name-history__empty {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}
</style>
