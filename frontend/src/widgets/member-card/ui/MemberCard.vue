<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TimeValue } from '@/entities/attempt'
import { MemberBadge, type ClubMemberCard, type MemberEventResult } from '@/entities/club'
import { RecordBadge } from '@/entities/record'
import { DisqualificationControl } from '@/features/disqualification'
import { BanControl } from '@/features/member-ban'
import { OrganizerSwitch } from '@/features/member-role'
import { PasswordResetButton } from '@/features/password-reset'
import { eventName, EVENTS, formatDate, plural } from '@/shared/lib'
import { AppCard, AppIcon, AppSelect, SettingRow } from '@/shared/ui'

// Member card for the organizer (on a wide screen, the right
// panel): meetups with results, "Access" and "Violations".
const { clubId, member, timeZone } = defineProps<{
  clubId: number
  member: ClubMemberCard
  timeZone: string
}>()
const emit = defineEmits<{
  /** The server returned an updated card. */
  changed: [member: ClubMemberCard]
  /** Something not in the response changed (disqualification): the card has to be reloaded. */
  reload: []
}>()

const COLLAPSED_MEETUPS = 3
const showAll = ref(false)
const visibleMeetups = computed(() =>
  showAll.value ? member.meetups : member.meetups.slice(0, COLLAPSED_MEETUPS),
)

const initials = computed(() =>
  member.user.display_name
    .split(' ')
    .slice(0, 2)
    .map((word) => word[0])
    .join(''),
)

const joined = computed(() =>
  new Intl.DateTimeFormat('ru', { month: 'long', year: 'numeric', timeZone })
    .format(new Date(member.joined_at)),
)

// Disqualification at a meetup: choosing among the meetups where the member competed.
const disqualifyMeetupId = ref('')
watch(
  () => member.user.id,
  () => (disqualifyMeetupId.value = member.meetups[0] ? String(member.meetups[0].id) : ''),
  { immediate: true },
)
const meetupOptions = computed(() =>
  member.meetups.map((m) => ({
    value: String(m.id),
    label: `${formatDate(m.date)}${m.disqualification ? ' — дисквалифицирован' : ''}`,
  })),
)
const disqualifyMeetup = computed(
  () => member.meetups.find((m) => String(m.id) === disqualifyMeetupId.value) ?? null,
)

/** The main result of a series: the average for ao5/mo3, otherwise the best attempt. */
function mainResult(result: MemberEventResult) {
  const isAverage = result.format === 'ao5' || result.format === 'mo3'
  return {
    value: isAverage ? result.average : result.best,
    isAverage,
    marks: isAverage ? result.marks.average : result.marks.single,
  }
}
</script>

<template>
  <div class="member-card">
    <AppCard class="member-card__head">
      <span class="member-card__avatar" aria-hidden="true">{{ initials }}</span>
      <div class="member-card__who">
        <h2 class="member-card__name">
          {{ member.user.display_name }}
          <MemberBadge v-if="member.role === 'organizer'" kind="organizer" />
          <MemberBadge v-if="member.ban" kind="banned" />
        </h2>
        <p class="member-card__muted">@{{ member.user.login }}</p>
        <p class="member-card__muted">
          В клубе с {{ joined }} ·
          {{ plural(member.meetups_count, ['встреча', 'встречи', 'встреч']) }}
        </p>
        <RouterLink
          class="member-card__profile"
          :to="{ name: 'user-profile', params: { userId: member.user.id } }"
        >
          Публичный профиль
        </RouterLink>
      </div>
    </AppCard>

    <AppCard class="member-card__section">
      <h3 class="member-card__heading">Результаты</h3>
      <p class="member-card__muted">Встречи клуба. Нажмите на встречу, чтобы исправить результаты.</p>

      <p v-if="member.meetups.length === 0" class="member-card__empty">
        На встречах клуба ещё не собирал.
      </p>
      <ul v-else class="member-card__meetups">
        <li v-for="meetup in visibleMeetups" :key="meetup.id">
          <RouterLink
            class="member-card__meetup"
            :to="{ name: 'series-edit', params: { meetupId: meetup.id, userId: member.user.id } }"
          >
            <span class="member-card__meetup-text">
              <span class="member-card__meetup-title">
                {{ formatDate(meetup.date) }}<template v-if="meetup.place"> · {{ meetup.place }}</template>
                <span v-if="meetup.status === 'live'" class="member-card__live">идёт</span>
              </span>
              <span v-if="meetup.disqualification" class="member-card__dq">
                Дисквалифицирован: {{ meetup.disqualification.reason }}
              </span>
              <span class="member-card__results">
                <span v-for="result in meetup.events" :key="result.event_id" class="member-card__result">
                  {{ eventName(result.event_id) }}:
                  <TimeValue
                    :value="mainResult(result).value"
                    :is-average="mainResult(result).isAverage"
                    :result-type="EVENTS[result.event_id].resultType"
                  />
                  <RecordBadge v-for="mark in mainResult(result).marks" :key="mark" :mark="mark" />
                  <span v-if="result.status === 'in_progress'" class="member-card__muted">
                    (не завершена)
                  </span>
                </span>
              </span>
            </span>
            <AppIcon name="chevron-right" :size="20" class="member-card__chevron" />
          </RouterLink>
        </li>
      </ul>
      <button
        v-if="member.meetups.length > COLLAPSED_MEETUPS"
        type="button"
        class="member-card__more"
        @click="showAll = !showAll"
      >
        {{ showAll ? 'Свернуть' : `Показать все ${plural(member.meetups.length, ['встречу', 'встречи', 'встреч'])}` }}
        <AppIcon :name="showAll ? 'expand-less' : 'expand-more'" :size="20" />
      </button>
    </AppCard>

    <AppCard class="member-card__section">
      <h3 class="member-card__heading">Доступ</h3>
      <div class="member-card__rows">
        <OrganizerSwitch :club-id="clubId" :member="member" @changed="emit('changed', $event)" />
        <PasswordResetButton
          :club-id="clubId"
          :user="member.user"
          :restriction="member.restrictions.reset_password"
        />
      </div>
    </AppCard>

    <AppCard class="member-card__section">
      <h3 class="member-card__heading">Нарушения</h3>
      <p class="member-card__muted">Требуют подтверждения с указанием причины.</p>
      <div class="member-card__rows">
        <SettingRow
          title="Дисквалифицировать на встрече"
          description="Результаты участника на выбранной встрече уходят из таблиц и рекордов. Серии сохраняются, дисквалификацию можно отменить."
          :restriction="member.meetups.length === 0 ? 'Нет встреч, где участник собирал' : null"
        >
          <template v-if="disqualifyMeetup" #details>
            <AppSelect
              v-model="disqualifyMeetupId"
              :options="meetupOptions"
              aria-label="Встреча"
              class="member-card__select"
            />
          </template>
          <DisqualificationControl
            v-if="disqualifyMeetup"
            :key="disqualifyMeetup.id"
            :meetup-id="disqualifyMeetup.id"
            :user="member.user"
            :disqualification="disqualifyMeetup.disqualification"
            @changed="emit('reload')"
          />
        </SettingRow>
        <BanControl
          :club-id="clubId"
          :member="member"
          :time-zone="timeZone"
          @changed="emit('changed', $event)"
        />
      </div>
    </AppCard>
  </div>
</template>

<style scoped>
.member-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.member-card__head {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.member-card__avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  background: var(--color-background);
  border-radius: 50%;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-heading);
}

.member-card__profile {
  font-size: var(--font-size-label);
}

.member-card__who {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.member-card__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  font-size: 18px;
  font-weight: var(--font-weight-heading);
  overflow-wrap: anywhere;
}

.member-card__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.member-card__heading {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.member-card__muted,
.member-card__empty {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.member-card__empty {
  padding: var(--space-3) 0;
}

.member-card__meetups,
.member-card__rows {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.member-card__meetups li + li,
.member-card__rows > * + * {
  border-top: 1px solid var(--color-border);
}

.member-card__meetup {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  color: inherit;
  text-decoration: none;
}

.member-card__meetup-text {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.member-card__meetup-title {
  font-weight: var(--font-weight-label);
}

.member-card__live {
  margin-left: var(--space-2);
  color: var(--color-danger);
  font-size: var(--font-size-label);
}

.member-card__dq {
  color: var(--color-danger);
  font-size: var(--font-size-label);
  overflow-wrap: anywhere;
}

.member-card__results {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  font-size: var(--font-size-label);
}

.member-card__result {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.member-card__chevron {
  flex-shrink: 0;
  color: var(--color-text-secondary);
}

.member-card__more {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: var(--space-1);
  padding: var(--space-2) 0;
  background: none;
  border: none;
  color: var(--color-primary);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.member-card__select {
  margin-top: var(--space-2);
}
</style>
