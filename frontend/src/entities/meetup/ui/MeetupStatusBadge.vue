<script setup lang="ts">
import { LiveIndicator } from '@/shared/ui'
import type { MeetupStatus } from '../model/types'

defineProps<{ status: MeetupStatus }>()

const LABELS: Record<MeetupStatus, string> = {
  planned: 'Анонс',
  live: 'Идёт',
  finished: 'Завершена',
  cancelled: 'Отменена',
}
</script>

<template>
  <LiveIndicator v-if="status === 'live'" />
  <span v-else :class="['meetup-status', `meetup-status--${status}`]">
    {{ LABELS[status] }}
  </span>
</template>

<style scoped>
.meetup-status {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 var(--space-2);
  border-radius: var(--radius-badge);
  font-size: 12px;
  font-weight: var(--font-weight-label);
}

.meetup-status--planned {
  background: color-mix(in srgb, var(--color-primary) 12%, var(--color-surface));
  color: var(--color-primary);
}

.meetup-status--finished,
.meetup-status--cancelled {
  background: var(--color-background);
  color: var(--color-text-secondary);
}
</style>
