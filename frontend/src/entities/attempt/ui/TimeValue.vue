<script setup lang="ts">
import { computed } from 'vue'
import { DNF, formatAttempt, formatResult, type Penalty, type ResultType } from '@/shared/lib'

// Time, average or move count. With penalty it is an attempt: value without the penalty,
// shown as "11.87 (+2)", DNF or DNS. Without penalty it is a final result.
const {
  value,
  penalty,
  resultType = 'time',
  isAverage = false,
  size = 'small',
} = defineProps<{
  value: number | null
  penalty?: Penalty
  resultType?: ResultType
  isAverage?: boolean
  size?: 'small' | 'large'
}>()

const text = computed(() =>
  penalty
    ? formatAttempt({ value, penalty }, resultType)
    : formatResult(value, resultType, isAverage),
)
const isDnf = computed(() =>
  penalty ? penalty === 'dnf' || penalty === 'dns' : value === DNF,
)
</script>

<template>
  <span
    :class="[
      'time-value',
      `time-value--${size}`,
      { 'time-value--dnf': isDnf, 'time-value--empty': !penalty && value === null },
    ]"
  >
    {{ text }}
  </span>
</template>

<style scoped>
.time-value {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.time-value--small {
  font-size: var(--font-size-time-small);
  font-weight: var(--font-weight-time-small);
}

.time-value--large {
  font-size: var(--font-size-time-large);
  font-weight: var(--font-weight-time-large);
}

.time-value--dnf {
  color: var(--color-dnf);
}

.time-value--empty {
  color: var(--color-text-secondary);
}
</style>
