<script setup lang="ts">
import { computed } from 'vue'
import { MeetupStatusBadge, type Meetup } from '@/entities/meetup'
import { JoinLinkCard } from '@/features/join-link'
import { StartMeetupButton } from '@/features/meetup-start'
import { RequestsBlock } from '@/features/participation-requests'
import { formatTime, plural } from '@/shared/lib'
import { AppCard } from '@/shared/ui'

// Панель встречи организатора (макеты org_meetup и org_meetup_desk):
// статус и запуск, QR-код со ссылкой, заявки. Участники, результаты
// и завершение встречи появятся в следующих шагах.
const { meetup } = defineProps<{ meetup: Meetup }>()
const emit = defineEmits<{
  /** Встреча изменилась (запуск, новая ссылка) — новые данные. */
  update: [meetup: Meetup]
  /** Изменились заявки: нужно перечитать встречу (число участников). */
  refresh: []
}>()

const startTime = computed(() => formatTime(meetup.starts_at, meetup.club.timezone))
const withToken = computed(() =>
  meetup.join_token ? { ...meetup, join_token: meetup.join_token } : null,
)

function onReissued(token: string) {
  emit('update', { ...meetup, join_token: token })
}
</script>

<template>
  <div class="meetup-panel">
    <div class="meetup-panel__column">
      <AppCard class="meetup-panel__status">
        <div class="meetup-panel__status-row">
          <MeetupStatusBadge :status="meetup.status" />
          <span class="meetup-panel__start">Старт {{ startTime }}</span>
        </div>
        <p>{{ plural(meetup.participants_count, ['участник', 'участника', 'участников']) }}</p>
        <StartMeetupButton
          v-if="meetup.status === 'planned'"
          :meetup-id="meetup.id"
          @started="emit('update', $event)"
        />
      </AppCard>

      <section v-if="withToken" class="meetup-panel__section">
        <h2 class="meetup-panel__heading">Материалы</h2>
        <JoinLinkCard :meetup="withToken" @reissued="onReissued" />
      </section>
    </div>

    <div class="meetup-panel__column">
      <RequestsBlock
        :meetup-id="meetup.id"
        :readonly="meetup.status === 'finished'"
        @changed="emit('refresh')"
      />
    </div>
  </div>
</template>

<style scoped>
.meetup-panel,
.meetup-panel__column,
.meetup-panel__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.meetup-panel__section {
  gap: var(--space-2);
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

.meetup-panel__heading {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

@media (min-width: 768px) {
  .meetup-panel {
    display: grid;
    grid-template-columns: minmax(0, 360px) minmax(0, 1fr);
    align-items: start;
    gap: var(--space-5);
  }
}
</style>
