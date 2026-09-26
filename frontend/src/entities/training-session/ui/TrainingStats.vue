<script setup lang="ts">
import { computed } from 'vue'
import { DNF, formatResult } from '@/shared/lib'
import type { SessionStats } from '../model/session'

// Session statistics tiles: ao5, ao12, best, number of solves.
const { stats } = defineProps<{ stats: SessionStats }>()

const tiles = computed(() => [
  { label: 'ao5', value: stats.ao5, text: formatResult(stats.ao5, 'time', true) },
  { label: 'ao12', value: stats.ao12, text: formatResult(stats.ao12, 'time', true) },
  { label: 'лучшая', value: stats.best, text: formatResult(stats.best, 'time') },
  { label: 'сборок', value: stats.count, text: String(stats.count) },
])
</script>

<template>
  <dl class="training-stats">
    <div v-for="tile in tiles" :key="tile.label" class="training-stats__tile">
      <dt class="training-stats__label">{{ tile.label }}</dt>
      <dd
        :class="[
          'training-stats__value',
          {
            'training-stats__value--dnf': tile.value === DNF,
            'training-stats__value--empty': tile.value === null,
          },
        ]"
      >
        {{ tile.text }}
      </dd>
    </div>
  </dl>
</template>

<style scoped>
.training-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
}

.training-stats__tile {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--color-background);
  border-radius: var(--radius-button);
}

.training-stats__label {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-label);
}

.training-stats__value {
  font-family: var(--font-mono);
  font-size: var(--font-size-time-large);
  font-weight: var(--font-weight-time-large);
  font-variant-numeric: tabular-nums;
}

.training-stats__value--dnf {
  color: var(--color-dnf);
}

.training-stats__value--empty {
  color: var(--color-text-secondary);
}

@media (min-width: 600px) {
  .training-stats {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
</style>
