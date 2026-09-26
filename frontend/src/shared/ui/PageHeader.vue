<script setup lang="ts">
import { useRouter, type RouteLocationRaw } from 'vue-router'
import AppIcon from './AppIcon.vue'

const { backTo } = defineProps<{
  title: string
  subtitle?: string
  /** Where the "back" arrow leads if there is no previous page in the history. Without it there is no arrow. */
  backTo?: RouteLocationRaw
}>()

const router = useRouter()

function goBack() {
  // Inside the app it is a regular step back, otherwise (opened by a link) it goes to backTo.
  if (window.history.state?.back) {
    router.back()
  } else if (backTo) {
    router.push(backTo)
  }
}
</script>

<template>
  <header class="page-header">
    <button v-if="backTo" type="button" class="page-header__back" aria-label="Назад" @click="goBack">
      <AppIcon name="arrow-back" />
    </button>
    <div class="page-header__text">
      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="subtitle" class="page-header__subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.action" class="page-header__action">
      <slot name="action" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.page-header__back {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: var(--control-height);
  height: var(--control-height);
  margin-left: calc(-1 * var(--space-3));
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius-button);
  cursor: pointer;
}

.page-header__back:focus-visible {
  outline: 2px solid var(--color-primary);
}

.page-header__text {
  flex: 1;
  min-width: 0;
}

.page-header__title {
  font-size: var(--font-size-heading);
  font-weight: var(--font-weight-heading);
  line-height: 1.3;
}

.page-header__subtitle {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.page-header__action {
  flex-shrink: 0;
}
</style>
