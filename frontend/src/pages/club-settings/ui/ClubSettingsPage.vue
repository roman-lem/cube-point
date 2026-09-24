<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchClub, useCurrentClubStore, type Club, type ClubPageData } from '@/entities/club'
import { ClubSettingsForm } from '@/features/club-settings'
import { ApiError } from '@/shared/api'
import { AppCard, PageHeader } from '@/shared/ui'

const { clubId } = defineProps<{ clubId: number }>()

const clubStore = useCurrentClubStore()
const data = ref<ClubPageData | null>(null)
const error = ref('')

onMounted(async () => {
  try {
    data.value = await fetchClub(clubId)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить клуб'
  }
})

function onSaved(club: Club) {
  data.value!.club = club
  // Название клуба в навигации.
  clubStore.load(true)
}
</script>

<template>
  <main class="page page--narrow">
    <PageHeader title="Настройки клуба" :back-to="{ name: 'club', params: { clubId } }" />
    <AppCard v-if="error">{{ error }}</AppCard>
    <!-- Права проверяет сервер; здесь только не показываем форму, которую нельзя сохранить. -->
    <AppCard v-else-if="data && data.my_role !== 'organizer'">
      Настройки клуба может менять только организатор
    </AppCard>
    <ClubSettingsForm v-else-if="data" :club="data.club" @saved="onSaved" />
  </main>
</template>
