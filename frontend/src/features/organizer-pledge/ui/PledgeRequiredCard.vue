<script setup lang="ts">
import { AppButton, AppCard } from '@/shared/ui'

// On organizer-only pages: the organizer has not accepted the pledge yet.
// The dialog with the text is on the club page.
defineProps<{ clubId: number }>()
</script>

<template>
  <AppCard class="pledge-required">
    <p>Инструменты организатора откроются, когда вы примете обязательство организатора.</p>
    <AppButton :to="{ name: 'club', params: { clubId } }">Перейти на страницу клуба</AppButton>
  </AppCard>
</template>

<style scoped>
.pledge-required {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
</style>
