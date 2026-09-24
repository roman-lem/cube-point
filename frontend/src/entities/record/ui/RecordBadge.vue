<script setup lang="ts">
import type { RecordMark } from '../model/types'

defineProps<{ mark: RecordMark }>()

const TITLES: Record<RecordMark, string> = {
  PB: 'Личный рекорд',
  LR: 'Рекорд клуба',
}
</script>

<template>
  <span :class="['record-badge', `record-badge--${mark}`]" :title="TITLES[mark]">{{ mark }}</span>
</template>

<style scoped>
.record-badge {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 6px;
  border-radius: var(--radius-badge);
  color: var(--color-on-primary);
  font-size: 11px;
  font-weight: var(--font-weight-heading);
  letter-spacing: 0.02em;
}

.record-badge--PB {
  background: var(--color-personal-best);
}

.record-badge--LR {
  background: var(--color-club-record);
}
</style>
