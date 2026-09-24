<script setup lang="ts">
import { AppCard, PageHeader } from '@/shared/ui'

// Заглушка для экранов, которых ещё нет (см. «Заглушки» в CLAUDE.md).
defineProps<{ title: string }>()
</script>

<template>
  <main class="page page--narrow">
    <PageHeader :title="title" />
    <AppCard class="page__muted">Скоро здесь появится этот раздел</AppCard>
  </main>
</template>
