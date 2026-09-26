<script setup lang="ts">
import { useIntervalFn, useMediaQuery } from '@vueuse/core'
import { computed, ref, watch } from 'vue'
import { fetchDesk, MeetupStatusBadge, type DeskEvent, type Meetup, type MeetupDesk } from '@/entities/meetup'
import { useAttemptSaving } from '@/features/attempt-edit'
import { JoinLinkCard } from '@/features/join-link'
import { FinishMeetupButton } from '@/features/meetup-finish'
import { StartMeetupButton } from '@/features/meetup-start'
import { AddParticipantButton } from '@/features/participant-add'
import { RequestsBlock } from '@/features/participation-requests'
import { ApiError } from '@/shared/api'
import { eventName, formatTime, plural } from '@/shared/lib'
import { AppCard, AppIcon } from '@/shared/ui'
import { EditableResultsTable } from '@/widgets/results-table'
import ParticipantList from './ParticipantList.vue'

// Organizer's meetup panel: status,
// start and finish, QR code and score sheets, requests, participants and manual entry.
// On a phone, a participant list with links to entry; on a wide screen,
// event tabs with a spreadsheet-like table.
const { meetup } = defineProps<{ meetup: Meetup }>()
const emit = defineEmits<{
  /** The meetup changed (start, finish, new link): new data. */
  update: [meetup: Meetup]
  /** Participants changed: the meetup has to be reloaded (participant count). */
  refresh: []
}>()

// Participants are submitting attempts right now, so the table refreshes itself.
const REFRESH_MS = 15_000

const isDesktop = useMediaQuery('(min-width: 1024px)')
const desk = ref<MeetupDesk | null>(null)
const error = ref('')
/** Tab on a wide screen: an event ID or the participant list. */
const tab = ref<string>('participants')

const startTime = computed(() => formatTime(meetup.starts_at, meetup.club.timezone))
const withLink = computed(() =>
  meetup.join_url ? { ...meetup, join_url: meetup.join_url } : null,
)
const editable = computed(() => meetup.status !== 'planned')

async function loadDesk() {
  try {
    desk.value = await fetchDesk(meetup.id)
    error.value = ''
    if (tab.value === 'participants' && isDesktop.value && editable.value) {
      tab.value = desk.value.events[0]?.event_id ?? 'participants'
    }
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить участников'
  }
}

watch(() => meetup.id, loadDesk, { immediate: true })
useIntervalFn(() => {
  if (meetup.status === 'live') {
    loadDesk()
  }
}, REFRESH_MS)

function replaceEvent(event: DeskEvent) {
  if (desk.value) {
    desk.value = {
      ...desk.value,
      events: desk.value.events.map((e) => (e.event_id === event.event_id ? event : e)),
    }
  }
}

const saving = useAttemptSaving({
  meetupId: () => meetup.id,
  version: (eventId, userId) =>
    desk.value?.events
      .find((e) => e.event_id === eventId)
      ?.rows.find((r) => r.user.id === userId)?.series?.version ?? null,
  onEvent: replaceEvent,
})

const progress = computed(() => {
  const series = desk.value?.events.flatMap((e) => e.rows.map((r) => r.series)).filter(Boolean) ?? []
  const completed = series.filter((s) => s!.status === 'completed').length
  return {
    completed,
    total: series.length,
    percent: series.length ? Math.round((completed / series.length) * 100) : 0,
  }
})

const activeEvent = computed(() => desk.value?.events.find((e) => e.event_id === tab.value))

function onReissued(link: { join_token: string; join_url: string }) {
  emit('update', { ...meetup, ...link })
}

function onFinished(finished: Meetup) {
  emit('update', finished)
  loadDesk()
}

function onParticipantsChanged() {
  loadDesk()
  emit('refresh')
}
</script>

<template>
  <div class="meetup-panel">
    <div class="meetup-panel__top">
      <AppCard class="meetup-panel__status">
        <div class="meetup-panel__status-row">
          <MeetupStatusBadge :status="meetup.status" />
          <span class="meetup-panel__start">Старт {{ startTime }}</span>
        </div>
        <p>
          {{ plural(meetup.participants_count, ['участник', 'участника', 'участников']) }}
          <template v-if="progress.total">
            · {{ progress.completed }} из {{ plural(progress.total, ['серии', 'серий', 'серий']) }}
          </template>
        </p>
        <div v-if="progress.total" class="meetup-panel__progress" aria-hidden="true">
          <div class="meetup-panel__progress-bar" :style="{ width: `${progress.percent}%` }" />
        </div>
        <StartMeetupButton
          v-if="meetup.status === 'planned'"
          :meetup-id="meetup.id"
          @started="emit('update', $event)"
        />
        <FinishMeetupButton
          v-else-if="meetup.status === 'live'"
          :meetup="meetup"
          @finished="onFinished"
        />
        <p v-else class="meetup-panel__muted">
          Встреча завершена. Результаты с бумажных бланков можно вносить и сейчас.
        </p>
      </AppCard>

      <section class="meetup-panel__section">
        <h2 class="meetup-panel__heading">Материалы</h2>
        <JoinLinkCard v-if="withLink" :meetup="withLink" @reissued="onReissued" />
        <RouterLink
          :to="{ name: 'scramble-print', params: { meetupId: meetup.id } }"
          class="meetup-panel__material"
        >
          <AppIcon name="print" />
          <span>
            <span class="meetup-panel__material-title">Бланки со скрамблами</span>
            <span class="meetup-panel__muted">Печать: два бланка A5 на листе A4</span>
          </span>
          <AppIcon name="chevron-right" :size="20" />
        </RouterLink>
      </section>

      <RequestsBlock
        :meetup-id="meetup.id"
        :readonly="meetup.status === 'finished'"
        @changed="onParticipantsChanged"
      />
    </div>

    <section class="meetup-panel__section">
      <div class="meetup-panel__participants-head">
        <h2 class="meetup-panel__title">
          Участники
          <span v-if="desk" class="meetup-panel__count">{{ desk.participants.length }}</span>
        </h2>
        <AddParticipantButton :meetup-id="meetup.id" @added="onParticipantsChanged" />
      </div>
      <p v-if="error" class="meetup-panel__error" role="alert">{{ error }}</p>

      <template v-if="desk">
        <template v-if="isDesktop">
          <div class="meetup-panel__tabs" role="tablist">
            <template v-if="editable">
              <button
                v-for="event in desk.events"
                :key="event.event_id"
                type="button"
                role="tab"
                :aria-selected="tab === event.event_id"
                :class="['meetup-panel__tab', { 'meetup-panel__tab--active': tab === event.event_id }]"
                @click="tab = event.event_id"
              >
                {{ eventName(event.event_id) }}
              </button>
            </template>
            <button
              type="button"
              role="tab"
              :aria-selected="tab === 'participants'"
              :class="['meetup-panel__tab', { 'meetup-panel__tab--active': tab === 'participants' }]"
              @click="tab = 'participants'"
            >
              Список участников
            </button>
          </div>
          <EditableResultsTable
            v-if="activeEvent && editable"
            :key="activeEvent.event_id"
            :event="activeEvent"
            :saving="saving"
            :time-zone="meetup.club.timezone"
          />
          <ParticipantList
            v-else
            :meetup-id="meetup.id"
            :desk="desk"
            :editable="editable"
            @changed="loadDesk"
          />
        </template>
        <ParticipantList
          v-else
          :meetup-id="meetup.id"
          :desk="desk"
          :editable="editable"
          @changed="loadDesk"
        />
      </template>
    </section>
  </div>
</template>

<style scoped>
.meetup-panel,
.meetup-panel__top,
.meetup-panel__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.meetup-panel__section {
  gap: var(--space-3);
}

.meetup-panel__status {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.meetup-panel__status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.meetup-panel__start {
  padding: 2px var(--space-2);
  background: var(--color-background);
  border-radius: var(--radius-badge);
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-label);
}

.meetup-panel__progress {
  height: 6px;
  overflow: hidden;
  background: var(--color-background);
  border-radius: 3px;
}

.meetup-panel__progress-bar {
  height: 100%;
  background: var(--color-primary);
}

.meetup-panel__heading {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.meetup-panel__material {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: inherit;
  text-decoration: none;
}

.meetup-panel__material > span {
  display: flex;
  flex: 1;
  flex-direction: column;
}

.meetup-panel__material-title {
  font-weight: var(--font-weight-label);
}

.meetup-panel__muted {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.meetup-panel__participants-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.meetup-panel__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.meetup-panel__count {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.meetup-panel__error {
  color: var(--color-danger);
}

.meetup-panel__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  border-bottom: 1px solid var(--color-border);
}

.meetup-panel__tab {
  height: 40px;
  padding: 0 var(--space-4);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.meetup-panel__tab--active {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
}

@media (min-width: 768px) {
  .meetup-panel__top {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
  }
}

@media (min-width: 1024px) {
  .meetup-panel__top {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
