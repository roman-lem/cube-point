<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  ClubLinks, ClubLogo, fetchClub, useCurrentClubStore, type ClubPageData,
} from '@/entities/club'
import { fetchClubMeetups, MeetupCard, type MeetupSummary } from '@/entities/meetup'
import { OrganizerPledgeDialog } from '@/features/organizer-pledge'
import { ApiError } from '@/shared/api'
import { todayIn } from '@/shared/lib'
import { AppCard, AppIcon } from '@/shared/ui'

const { clubId } = defineProps<{ clubId: number }>()

const clubStore = useCurrentClubStore()
const data = ref<ClubPageData | null>(null)
const meetups = ref<MeetupSummary[]>([])
const error = ref('')

watch(
  () => clubId,
  async (id) => {
    error.value = ''
    try {
      ;[data.value, meetups.value] = await Promise.all([fetchClub(id), fetchClubMeetups(id)])
      clubStore.setClubId(id)
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить клуб'
    }
  },
  { immediate: true },
)

// Organizer tools open only after the organizer pledge is accepted.
const isOrganizer = computed(() => data.value?.my_role === 'organizer' && !data.value.pledge)
// A cancelled meetup stays among the upcoming ones until its date has passed.
function isPast(meetup: MeetupSummary) {
  return (
    meetup.status === 'finished' ||
    (meetup.status === 'cancelled' && meetup.date < todayIn(data.value!.club.timezone))
  )
}

// The server returns meetups newest first; upcoming ones are shown in date order.
const upcoming = computed(() => meetups.value.filter((m) => !isPast(m)).reverse())
const past = computed(() => meetups.value.filter(isPast))
// Cancelled meetups are not counted.
const pastHeld = computed(() => past.value.filter((m) => m.status === 'finished').length)
const scheduled = computed(() => upcoming.value.filter((m) => m.status !== 'cancelled'))
// For an organizer, "Manage" leads to the live or the upcoming meetup.
const currentMeetup = computed(
  () => scheduled.value.find((m) => m.status === 'live') ?? scheduled.value[0] ?? null,
)

const meetupRoute = (meetup: MeetupSummary) => ({
  name: 'meetup',
  params: { meetupId: meetup.id },
})
</script>

<template>
  <main class="page">
    <AppCard v-if="error">{{ error }}</AppCard>

    <template v-else-if="data">
      <OrganizerPledgeDialog
        v-if="data.pledge"
        :club-id="clubId"
        :pledge="data.pledge"
        @accepted="data.pledge = null"
      />

      <header class="club-page__header">
        <div class="club-page__title-row">
          <ClubLogo :name="data.club.name" :color="data.club.logo_color" />
          <div>
            <h1 class="club-page__name">{{ data.club.name }}</h1>
            <p class="club-page__city">
              <AppIcon name="location" :size="18" />
              {{ data.club.city }}
            </p>
          </div>
        </div>
        <p v-if="data.club.description" class="club-page__description">
          {{ data.club.description }}
        </p>
        <ClubLinks :links="data.club.links" />
      </header>

      <nav class="club-page__actions" aria-label="Разделы клуба">
        <RouterLink class="club-page__action" :to="{ name: 'club-records', params: { clubId } }">
          <AppIcon name="trophy" :size="20" />
          Рекорды
        </RouterLink>
        <RouterLink class="club-page__action" :to="{ name: 'club-members', params: { clubId } }">
          <AppIcon name="group" :size="20" />
          Участники
        </RouterLink>
      </nav>

      <nav v-if="isOrganizer" class="club-page__actions" aria-label="Управление клубом">
        <RouterLink
          v-if="currentMeetup"
          class="club-page__action"
          :to="{ name: 'meetup-manage', params: { meetupId: currentMeetup.id } }"
        >
          <AppIcon name="qr-code" :size="20" />
          Управление
        </RouterLink>
        <RouterLink class="club-page__action" :to="{ name: 'club-settings', params: { clubId } }">
          <AppIcon name="settings" :size="20" />
          Настройки
        </RouterLink>
        <RouterLink
          class="club-page__action club-page__action--primary"
          :to="{ name: 'meetup-create', params: { clubId } }"
        >
          <AppIcon name="add" :size="20" />
          Новая встреча
        </RouterLink>
      </nav>

      <section class="page__section">
        <h2 class="page__section-title">
          {{ scheduled.length > 1 ? 'Ближайшие встречи' : 'Ближайшая встреча' }}
        </h2>
        <MeetupCard
          v-for="meetup in upcoming"
          :key="meetup.id"
          :meetup="meetup"
          :timezone="data.club.timezone"
          :to="meetupRoute(meetup)"
        />
        <p v-if="scheduled.length === 0" class="page__muted">Встреча пока не назначена</p>
      </section>

      <section v-if="past.length" class="page__section">
        <div class="club-page__section-header">
          <h2 class="page__section-title">Прошедшие встречи</h2>
          <span class="club-page__total">Всего {{ pastHeld }}</span>
        </div>
        <MeetupCard
          v-for="meetup in past"
          :key="meetup.id"
          :meetup="meetup"
          :timezone="data.club.timezone"
          :to="meetupRoute(meetup)"
          variant="compact"
        />
      </section>
    </template>
  </main>
</template>

<style scoped>
.club-page__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.club-page__title-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.club-page__name {
  font-size: var(--font-size-heading);
  font-weight: var(--font-weight-heading);
  line-height: 1.3;
}

.club-page__city {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-text-secondary);
}

.club-page__description {
  color: var(--color-text-secondary);
  white-space: pre-line;
}

.club-page__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}

.club-page__action {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  height: var(--control-height);
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  color: var(--color-text-primary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  text-decoration: none;
  white-space: nowrap;
}

.club-page__action--primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-on-primary);
}

/* Without the "Manage" button, "New meetup" is alone in the row, full width. */
.club-page__action:nth-child(odd):last-child {
  grid-column: 1 / -1;
}

.club-page__section-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.club-page__total {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-label);
}

@media (min-width: 768px) {
  .club-page__actions {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
