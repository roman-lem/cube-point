<script setup lang="ts">
// Setting row: title and description on the left, an action on the right (slot).
// restriction is why the action is unavailable: it is shown under the description
// so a disabled button is not a mystery.
defineProps<{ title: string; description: string; restriction?: string | null }>()
</script>

<template>
  <div class="setting-row">
    <div class="setting-row__text">
      <p class="setting-row__title">{{ title }}</p>
      <p class="setting-row__description">{{ description }}</p>
      <p v-if="restriction" class="setting-row__restriction">{{ restriction }}</p>
      <slot name="details" />
    </div>
    <div class="setting-row__action">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.setting-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3) 0;
}

.setting-row__text {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.setting-row__title {
  font-weight: var(--font-weight-label);
}

.setting-row__description {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.setting-row__restriction {
  color: var(--color-text-primary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.setting-row__action {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

@media (min-width: 640px) {
  .setting-row {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .setting-row__action {
    flex-shrink: 0;
    justify-content: flex-end;
  }
}
</style>
