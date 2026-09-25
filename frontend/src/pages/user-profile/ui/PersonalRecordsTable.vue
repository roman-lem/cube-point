<script setup lang="ts">
import { TimeValue } from '@/entities/attempt'
import type { UserProfile } from '@/entities/user'
import { EVENTS, eventName, movesWord } from '@/shared/lib'

// Таблица личных рекордов (макет personal_records): сингл и среднее по дисциплинам.
// Нет удачных результатов или среднего (bo-форматы) — «—», а не DNF.
defineProps<{ records: UserProfile['personal_records'] }>()
</script>

<template>
  <table class="pb-table">
    <thead>
      <tr>
        <th scope="col">Дисциплина</th>
        <th scope="col" class="pb-table__number">Сингл</th>
        <th scope="col" class="pb-table__number">Среднее</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="record in records" :key="record.event_id">
        <th scope="row">{{ eventName(record.event_id) }}</th>
        <td v-for="type in (['single', 'average'] as const)" :key="type" class="pb-table__number">
          <TimeValue
            :value="record[type]?.value ?? null"
            :result-type="EVENTS[record.event_id]?.resultType ?? 'time'"
            :is-average="type === 'average'"
          />
          <span
            v-if="record[type] && EVENTS[record.event_id]?.resultType === 'moves'"
            class="pb-table__unit"
          >
            {{ movesWord(record[type]!.value, type === 'average') }}
          </span>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.pb-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  border-style: hidden;
  box-shadow: 0 0 0 1px var(--color-border);
  overflow: hidden;
}

.pb-table th,
.pb-table td {
  padding: var(--space-3);
  text-align: left;
}

.pb-table thead th {
  background: var(--color-background);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-label);
}

.pb-table tbody tr + tr {
  border-top: 1px solid var(--color-border);
}

.pb-table tbody th {
  font-weight: var(--font-weight-label);
}

.pb-table .pb-table__number {
  text-align: right;
  white-space: nowrap;
}

.pb-table__unit {
  margin-left: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 12px;
}
</style>
