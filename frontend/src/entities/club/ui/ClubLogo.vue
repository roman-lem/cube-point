<script setup lang="ts">
import { computed } from 'vue'
import type { LogoColor } from '../model/types'

const { name, color, size = 56 } = defineProps<{
  name: string
  color: LogoColor
  size?: number
}>()

const letter = computed(() => name.trim().charAt(0).toUpperCase())
</script>

<template>
  <span
    class="club-logo"
    :style="{
      width: `${size}px`,
      height: `${size}px`,
      fontSize: `${Math.round(size * 0.45)}px`,
      background: `var(--color-logo-${color})`,
    }"
    aria-hidden="true"
  >
    {{ letter }}
  </span>
</template>

<style scoped>
.club-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: var(--radius-card);
  color: var(--color-on-primary);
  font-weight: var(--font-weight-heading);
}
</style>
