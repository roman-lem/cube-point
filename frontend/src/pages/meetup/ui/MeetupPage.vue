<script setup lang="ts">
import { useIntervalFn } from '@vueuse/core'
import { computed, ref, watch } from 'vue'
import { useCurrentClubStore } from '@/entities/club'
import { EventCard, fetchMeetup, MeetupHeader, type MeetupPageData } from '@/entities/meetup'
import { ApiError } from '@/shared/api'
import { AppCard, AppIcon } from '@/shared/ui'

const { meetupId } = defineProps<{ meetupId: number }>()

// Пока заявка ждёт подтверждения, страница сама проверяет её статус.
const PENDING_REFRESH_MS = 15_000

const clubStore = useCurrentClubStore()
const data = ref<MeetupPageData | null>(null)
const error = ref('')

async function load() {
  try {
    data.value = await fetchMeetup(meetupId)
    clubStore.setClubId(data.value.meetup.club.id)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить встречу'
  }
}

watch(() => meetupId, load, { immediate: true })

const requestStatus = computed(() => data.value?.my_request?.status ?? null)
const isOrganizer = computed(() => data.value?.my_role === 'organizer')

useIntervalFn(() => {
  if (requestStatus.value === 'pending') {
    load()
  }
}, PENDING_REFRESH_MS)

// Серию можно начать только подтверждённому участнику и только во время встречи
// (сервер проверяет это же). Ожидающие видят кнопку, но она неактивна.
const canSolve = computed(
  () => requestStatus.value === 'approved' && data.value?.meetup.status === 'live',
)
const showSolveButton = computed(
  () => requestStatus.value === 'approved' || requestStatus.value === 'pending',
)

const participation = computed(() => {
  const meetup = data.value?.meetup
  if (!meetup || meetup.status === 'finished') {
    return null
  }
  switch (requestStatus.value) {
    case 'approved':
      return {
        title: 'Вы участник встречи',
        text: meetup.status === 'planned' ? 'Серии можно начинать после старта встречи' : '',
      }
    case 'pending':
      return {
        title: 'Ожидаем подтверждения организатора',
        text: 'Дисциплины откроются, когда организатор подтвердит заявку',
      }
    case 'rejected':
      return { title: 'Заявка отклонена', text: 'Если это ошибка, подойдите к организатору' }
    default:
      return isOrganizer.value
        ? null
        : { title: 'Хотите участвовать?', text: 'Отсканируйте QR-код встречи у организатора' }
  }
})
</script>

<template>
  <main class="page">
    <AppCard v-if="error">{{ error }}</AppCard>

    <template v-else-if="data">
      <MeetupHeader :meetup="data.meetup" />

      <RouterLink
        v-if="isOrganizer"
        class="meetup-page__manage"
        :to="{ name: 'meetup-manage', params: { meetupId } }"
      >
        <AppIcon name="settings" :size="20" />
        Панель встречи
      </RouterLink>

      <div
        v-if="participation"
        :class="['meetup-page__participation', `meetup-page__participation--${requestStatus}`]"
        role="status"
      >
        <AppIcon :name="requestStatus === 'pending' ? 'schedule' : 'account'" />
        <div>
          <p class="meetup-page__participation-title">{{ participation.title }}</p>
          <p v-if="participation.text" class="meetup-page__participation-text">
            {{ participation.text }}
          </p>
        </div>
      </div>

      <section class="meetup-page__events">
        <EventCard
          v-for="event in data.meetup.events"
          :key="event.id"
          :event-id="event.event_id"
          :format="event.format"
          :participants-count="event.participants_count"
        >
          <template v-if="showSolveButton" #action>
            <RouterLink v-if="canSolve" class="meetup-page__solve" :to="{ name: 'timer' }">
              <AppIcon name="play" :size="18" />
              Собрать
            </RouterLink>
            <span v-else class="meetup-page__solve meetup-page__solve--locked" aria-disabled="true">
              <AppIcon name="lock" :size="18" />
              Собрать
            </span>
          </template>
        </EventCard>
      </section>
    </template>
  </main>
</template>

<style scoped>
.meetup-page__manage {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  height: var(--control-height);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.meetup-page__participation {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: color-mix(in srgb, var(--color-primary) 6%, var(--color-surface));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: var(--color-primary);
}

.meetup-page__participation svg {
  flex-shrink: 0;
}

.meetup-page__participation-title {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-label);
}

.meetup-page__participation-text {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.meetup-page__events {
  display: grid;
  gap: var(--space-3);
}

.meetup-page__solve {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: var(--space-1);
  height: 40px;
  padding: 0 var(--space-4);
  background: var(--color-primary);
  border-radius: var(--radius-button);
  color: var(--color-on-primary);
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.meetup-page__solve--locked {
  background: var(--color-background);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  cursor: not-allowed;
}

@media (min-width: 768px) {
  .meetup-page__events {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
