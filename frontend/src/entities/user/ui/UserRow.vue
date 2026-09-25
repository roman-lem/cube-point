<script setup lang="ts">
import { computed } from 'vue'

// Строка пользователя: инициалы, имя и логин, справа — действие (слот).
// Слот badges — отметки после имени, details — текст после логина через «·».
// Логин видят только организаторы и администратор: без него строка — имя и details.
const { displayName } = defineProps<{ displayName: string; login?: string; details?: string }>()

const initials = computed(() =>
  displayName
    .split(' ')
    .slice(0, 2)
    .map((word) => word[0])
    .join(''),
)
</script>

<template>
  <div class="user-row">
    <span class="user-row__avatar" aria-hidden="true">{{ initials }}</span>
    <span class="user-row__who">
      <span class="user-row__name">
        {{ displayName }}
        <slot name="badges" />
      </span>
      <span v-if="login" class="user-row__login">@{{ login }}<template v-if="details"> · {{ details }}</template></span>
      <span v-else-if="details" class="user-row__login">{{ details }}</span>
    </span>
    <slot />
  </div>
</template>

<style scoped>
.user-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 56px;
}

.user-row__avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: var(--color-background);
  border-radius: 50%;
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.user-row__who {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.user-row__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-2);
  font-weight: var(--font-weight-label);
  overflow-wrap: anywhere;
}

.user-row__login {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  overflow-wrap: anywhere;
}
</style>
