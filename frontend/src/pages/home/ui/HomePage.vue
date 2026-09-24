<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCurrentClubStore } from '@/entities/club'
import { AppCard, PageHeader } from '@/shared/ui'

// Главная — переход в текущий клуб: последний открытый или первый из списка.
const router = useRouter()
const clubStore = useCurrentClubStore()
const empty = ref(false)

onMounted(async () => {
  await clubStore.load()
  if (clubStore.club) {
    router.replace({ name: 'club', params: { clubId: clubStore.club.id } })
  } else {
    empty.value = true
  }
})
</script>

<template>
  <main v-if="empty" class="page">
    <PageHeader title="Клуб" />
    <AppCard>Клубов пока нет</AppCard>
  </main>
</template>

