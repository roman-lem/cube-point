<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchClub, type ClubPageData } from '@/entities/club'
import type { Meetup } from '@/entities/meetup'
import { MeetupCreateForm } from '@/features/meetup-create'
import { ApiError } from '@/shared/api'
import { AppCard, PageHeader } from '@/shared/ui'

const { clubId } = defineProps<{ clubId: number }>()

const router = useRouter()
const data = ref<ClubPageData | null>(null)
const error = ref('')

onMounted(async () => {
  try {
    data.value = await fetchClub(clubId)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить клуб'
  }
})

function onCreated(meetup: Meetup) {
  router.replace({ name: 'meetup-manage', params: { meetupId: meetup.id } })
}
</script>

<template>
  <main class="page page--narrow">
    <PageHeader title="Новая встреча" :back-to="{ name: 'club', params: { clubId } }" />
    <AppCard v-if="error">{{ error }}</AppCard>
    <AppCard v-else-if="data && data.my_role !== 'organizer'">
      Создавать встречи может только организатор клуба
    </AppCard>
    <MeetupCreateForm
      v-else-if="data"
      :club-id="clubId"
      :timezone="data.club.timezone"
      @created="onCreated"
    />
  </main>
</template>
