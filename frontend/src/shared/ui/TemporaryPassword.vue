<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from './AppIcon.vue'

// Логин и временный пароль, который показывается один раз, с кнопкой копирования.
const { login, password } = defineProps<{ login: string; password: string }>()

const copied = ref(false)

async function copy() {
  try {
    await navigator.clipboard.writeText(password)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    // Пароль виден на экране, его можно переписать вручную.
  }
}
</script>

<template>
  <dl class="temporary-password">
    <dt>Логин</dt>
    <dd>{{ login }}</dd>
    <dt>Пароль</dt>
    <dd>
      {{ password }}
      <button
        type="button"
        class="temporary-password__copy"
        :aria-label="copied ? 'Пароль скопирован' : 'Скопировать пароль'"
        @click="copy"
      >
        <AppIcon :name="copied ? 'check' : 'copy'" :size="18" />
      </button>
    </dd>
  </dl>
</template>

<style scoped>
.temporary-password {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-2) var(--space-4);
  margin: 0;
  padding: var(--space-3);
  background: var(--color-background);
  border-radius: var(--radius-button);
}

.temporary-password dt {
  color: var(--color-text-secondary);
}

.temporary-password dd {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 18px;
  overflow-wrap: anywhere;
}

.temporary-password__copy {
  display: inline-flex;
  padding: 0;
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
}
</style>
