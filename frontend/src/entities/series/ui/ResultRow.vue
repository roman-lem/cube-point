<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'
import { plural } from '@/shared/lib'
import { AppIcon } from '@/shared/ui'

// A result table row. The time and record marks are passed via slots
// (TimeValue and RecordBadge are in other entities slices), the expanded part
// (usually AttemptSeries) via the default slot.
//
// The name links to the profile; tapping anywhere else expands the row:
// the expand button is stretched over the whole row (::after) and the link lies on top of it.
// This way the link is not inside the button.
const expanded = defineModel<boolean>('expanded', { default: false })

defineProps<{
  place: number | null
  name: string
  /** The member profile the name links to. */
  profileTo?: RouteLocationRaw
  /** The current user's row: highlight and the "You" label. */
  isMe?: boolean
  /** Caption under the main result: ao5, mo3, bo3… */
  resultLabel: string
  /** For an unfinished series: how many attempts are submitted out of the total. */
  progress?: { done: number; total: number }
}>()
</script>

<template>
  <article :class="['result-row', { 'result-row--me': isMe, 'result-row--open': expanded }]">
    <div class="result-row__main">
      <span class="result-row__place">{{ place ?? '—' }}</span>
      <span class="result-row__who">
        <span class="result-row__name">
          <RouterLink v-if="profileTo" :to="profileTo" class="result-row__link">{{ name }}</RouterLink>
          <template v-else>{{ name }}</template>
          <span v-if="isMe" class="result-row__me">Вы</span>
        </span>
        <span v-if="$slots.single" class="result-row__single">
          лучшая: <slot name="single" />
        </span>
        <span v-if="progress" class="result-row__progress">
          {{ progress.done }} из {{ plural(progress.total, ['попытки', 'попыток', 'попыток']) }}
        </span>
      </span>
      <span class="result-row__result">
        <slot name="result" />
        <span class="result-row__label">{{ resultLabel }}</span>
      </span>
      <button
        type="button"
        class="result-row__toggle"
        :aria-expanded="expanded"
        :aria-label="`Попытки: ${name}`"
        @click="expanded = !expanded"
      >
        <AppIcon :name="expanded ? 'expand-less' : 'expand-more'" :size="20" />
      </button>
    </div>
    <div v-if="expanded" class="result-row__details">
      <slot />
    </div>
  </article>
</template>

<style scoped>
.result-row {
  position: relative;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  overflow: hidden;
}

.result-row--me {
  background: color-mix(in srgb, var(--color-primary) 6%, var(--color-surface));
}

.result-row--me::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 4px;
  background: var(--color-primary);
}

.result-row__main {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3) var(--space-3) var(--space-4);
}

.result-row__toggle {
  display: flex;
  flex-shrink: 0;
  padding: 0;
  background: none;
  border: 0;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.result-row__toggle::after {
  content: '';
  position: absolute;
  inset: 0;
}

.result-row__toggle:focus-visible {
  outline: none;
}

.result-row__toggle:focus-visible::after {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}

.result-row__link {
  position: relative;
  z-index: 1;
  color: inherit;
  text-decoration: none;
}

.result-row__link:hover {
  color: var(--color-primary);
  text-decoration: underline;
}

.result-row__place {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--color-background);
  border-radius: 50%;
  font-family: var(--font-mono);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  font-variant-numeric: tabular-nums;
}

.result-row__who {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.result-row__name {
  overflow: hidden;
  font-weight: var(--font-weight-label);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-row__me {
  margin-left: var(--space-1);
  padding: 1px 6px;
  background: var(--color-primary);
  border-radius: var(--radius-badge);
  color: var(--color-on-primary);
  font-size: 11px;
}

.result-row__single,
.result-row__progress {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
}

.result-row__result {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.result-row__label {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.result-row__details {
  padding: 0 var(--space-3) var(--space-3) var(--space-4);
}
</style>
