<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useCurrentClubStore } from '@/entities/club'
import { fetchMeetup, type Meetup, type MeetupPageData } from '@/entities/meetup'
import { PledgeRequiredCard } from '@/features/organizer-pledge'
import { ApiError } from '@/shared/api'
import { formatDate, latestLoader } from '@/shared/lib'
import { AppCard, PageHeader } from '@/shared/ui'
import { MeetupPanel } from '@/widgets/meetup-panel'

const { meetupId } = defineProps<{ meetupId: number }>()

const clubStore = useCurrentClubStore()
const data = ref<MeetupPageData | null>(null)
const error = ref('')

// The panel asks to reload the meetup while it is live: a slow old response
// must not overwrite the status after start or finish.
const { load, invalidate } = latestLoader(
  () => fetchMeetup(meetupId),
  (page) => {
    data.value = page
    error.value = ''
  },
  (e) => {
    // A connection error during refresh does not hide the panel already shown.
    if (!data.value) {
      error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить встречу'
    }
  },
)

watch(() => meetupId, () => {
  data.value = null
  error.value = ''
  load()
}, { immediate: true })

const subtitle = computed(() =>
  data.value ? `Встреча клуба, ${formatDate(data.value.meetup.date)}` : undefined,
)

function onUpdate(meetup: Meetup) {
  invalidate()
  const statusChanged = data.value?.meetup.status !== meetup.status
  data.value = { ...data.value!, meetup }
  if (statusChanged) {
    // LIVE indicator on the "Club" tab.
    clubStore.load(true)
  }
}
</script>

<template>
  <main class="page page--wide">
    <PageHeader
      title="Панель встречи"
      :subtitle="subtitle"
      :back-to="{ name: 'meetup', params: { meetupId } }"
    />
    <AppCard v-if="error">{{ error }}</AppCard>
    <AppCard v-else-if="data && data.my_role !== 'organizer'">
      Панель встречи доступна только организатору клуба
    </AppCard>
    <PledgeRequiredCard v-else-if="data?.pledge" :club-id="data.meetup.club.id" />
    <MeetupPanel v-else-if="data" :meetup="data.meetup" @update="onUpdate" @refresh="load" />
  </main>
</template>
