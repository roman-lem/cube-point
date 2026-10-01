<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchClub, type ClubPageData } from '@/entities/club'
import { fetchClubMeetups, type Meetup, type MeetupSummary } from '@/entities/meetup'
import { MeetupCreateForm } from '@/features/meetup-create'
import { PledgeRequiredCard } from '@/features/organizer-pledge'
import { ApiError } from '@/shared/api'
import { AppCard, PageHeader } from '@/shared/ui'

const { clubId } = defineProps<{ clubId: number }>()

const router = useRouter()
const data = ref<ClubPageData | null>(null)
/** The club's latest meetup by date: the form takes time, place and address from it. */
const previous = ref<MeetupSummary | null>(null)
const error = ref('')

onMounted(async () => {
  try {
    const [club, meetups] = await Promise.all([fetchClub(clubId), fetchClubMeetups(clubId)])
    // The server returns meetups newest first.
    previous.value = meetups[0] ?? null
    data.value = club
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
    <PledgeRequiredCard v-else-if="data?.pledge" :club-id="clubId" />
    <MeetupCreateForm
      v-else-if="data"
      :club-id="clubId"
      :timezone="data.club.timezone"
      :previous="previous"
      @created="onCreated"
    />
  </main>
</template>
