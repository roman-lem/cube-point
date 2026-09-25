<script setup lang="ts">
// Отметка у имени участника клуба: организатор или заблокирован.
defineProps<{ kind: 'organizer' | 'banned' }>()
</script>

<template>
  <span :class="['member-badge', `member-badge--${kind}`]">
    {{ kind === 'organizer' ? 'Орг' : 'Заблокирован' }}
  </span>
</template>

<style scoped>
.member-badge {
  padding: 0 var(--space-2);
  border: 1px solid currentColor;
  border-radius: var(--radius-badge);
  font-size: 12px;
  font-weight: var(--font-weight-label);
  line-height: 18px;
}

.member-badge--organizer {
  color: var(--color-primary);
}

.member-badge--banned {
  color: var(--color-danger);
}
</style>
