<script setup lang="ts">
import { DeletedNames } from '@/features/deleted-name'
import { PageHeader } from '@/shared/ui'

// Administration: names of deleted accounts in results and records.
</script>

<template>
  <main class="page page--narrow">
    <PageHeader
      title="Имена удалённых аккаунтов"
      subtitle="Отзыв согласия на имя в результатах и рекордах"
      :back-to="{ name: 'profile-settings' }"
    />
    <DeletedNames />
  </main>
</template>
