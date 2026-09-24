<script setup lang="ts">
import { LINK_NAMES } from '../model/links'
import type { ClubLink } from '../model/types'

defineProps<{ links: ClubLink[] }>()
</script>

<template>
  <ul v-if="links.length" class="club-links">
    <li v-for="link in links" :key="link.url">
      <a class="club-links__item" :href="link.url" target="_blank" rel="noopener noreferrer">
        {{ LINK_NAMES[link.type] }}
      </a>
    </li>
  </ul>
</template>

<style scoped>
.club-links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.club-links__item {
  display: inline-flex;
  align-items: center;
  height: 36px;
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  color: var(--color-text-primary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.club-links__item:hover {
  border-color: var(--color-primary);
}
</style>
