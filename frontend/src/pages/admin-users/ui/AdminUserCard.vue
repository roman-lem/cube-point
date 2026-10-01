<script setup lang="ts">
import { computed, ref } from 'vue'
import { TimeValue } from '@/entities/attempt'
import { MemberBadge, type MemberEventResult } from '@/entities/club'
import { RecordBadge } from '@/entities/record'
import { NameHistory } from '@/entities/user'
import { AnonymizeButton } from '@/features/deleted-name'
import { PasswordResetButton } from '@/features/password-reset'
import { eventName, EVENTS, formatDate } from '@/shared/lib'
import { ApiError } from '@/shared/api'
import { AppButton, AppCard, ConfirmDialog, FormError, SettingRow } from '@/shared/ui'
import { revertUserName, type AdminUserCard } from '../api/adminUsersApi'

// The administrator's user card: account data, clubs, consents, name history,
// meetups with results in all clubs, password reset, name revert and anonymization.
const { user } = defineProps<{ user: AdminUserCard }>()
const emit = defineEmits<{ changed: [] }>()

// A moment with the year, in the administrator's own time zone.
const momentFormat = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

function formatMoment(isoMoment: string) {
  return momentFormat.format(new Date(isoMoment))
}

const CONSENTS = [
  { type: 'processing', label: 'Обработка персональных данных' },
  { type: 'publication', label: 'Распространение' },
  { type: 'age', label: 'Подтверждение возраста' },
  { type: 'deleted_name', label: 'Имя оставлено после удаления' },
] as const

const consents = computed(() =>
  CONSENTS.flatMap(({ type, label }) => {
    const entry = user.consents[type]
    return entry ? [{ type, label, ...entry }] : []
  }),
)

// Returning the previous name: not the user's own change, their limit stays.
const revertOpen = ref(false)
const reverting = ref(false)
const revertError = ref('')
const previousName = computed(() => user.name_history[0]?.old_name ?? '')

function askRevert() {
  revertError.value = ''
  revertOpen.value = true
}

async function revertName() {
  reverting.value = true
  revertError.value = ''
  try {
    await revertUserName(user.id)
    revertOpen.value = false
    emit('changed')
  } catch (e) {
    revertError.value = e instanceof ApiError ? e.message : 'Не удалось вернуть имя'
  } finally {
    reverting.value = false
  }
}

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
  <div class="user-card">
    <AppCard class="user-card__section">
      <h2 class="user-card__name">
        {{ user.display_name }}
        <span v-if="user.is_admin" class="user-card__mark">Админ</span>
      </h2>
      <dl class="user-card__facts">
        <dt>Логин</dt>
        <dd>{{ user.login ? `@${user.login}` : '—' }}</dd>
        <dt>Почта</dt>
        <dd>{{ user.email ?? '—' }}</dd>
        <dt>Регистрация</dt>
        <dd>{{ formatMoment(user.created_at) }}</dd>
        <template v-if="user.deleted_at">
          <dt>Удалён</dt>
          <dd>
            {{ formatMoment(user.deleted_at) }}
            <template v-if="user.kept_name">, имя оставлено в результатах</template>
          </dd>
        </template>
      </dl>
      <RouterLink
        v-if="!user.kept_name"
        class="user-card__link"
        :to="{ name: 'user-profile', params: { userId: user.id } }"
      >
        Публичный профиль
      </RouterLink>
    </AppCard>

    <AppCard class="user-card__section">
      <h3 class="user-card__heading">Клубы</h3>
      <p v-if="user.clubs.length === 0" class="user-card__muted">Не состоит в клубах.</p>
      <ul v-else class="user-card__list">
        <li v-for="club in user.clubs" :key="club.id" class="user-card__club">
          <RouterLink :to="{ name: 'club', params: { clubId: club.id } }">{{ club.name }}</RouterLink>
          <MemberBadge v-if="club.role === 'organizer'" kind="organizer" />
          <MemberBadge v-if="club.banned" kind="banned" />
        </li>
      </ul>
    </AppCard>

    <AppCard class="user-card__section">
      <h3 class="user-card__heading">История имён</h3>
      <NameHistory :history="user.name_history" />
    </AppCard>

    <AppCard class="user-card__section">
      <h3 class="user-card__heading">Согласия</h3>
      <p v-if="consents.length === 0" class="user-card__muted">Согласий нет.</p>
      <dl v-else class="user-card__facts">
        <template v-for="consent in consents" :key="consent.type">
          <dt>{{ consent.label }}</dt>
          <dd>{{ formatMoment(consent.accepted_at) }}, версия {{ consent.version }}</dd>
        </template>
      </dl>
    </AppCard>

    <AppCard class="user-card__section">
      <h3 class="user-card__heading">Результаты</h3>
      <p v-if="user.meetups.length === 0" class="user-card__muted">На встречах ещё не собирал.</p>
      <ul v-else class="user-card__list user-card__list--divided">
        <li v-for="meetup in user.meetups" :key="meetup.id" class="user-card__meetup">
          <RouterLink class="user-card__meetup-title" :to="{ name: 'meetup', params: { meetupId: meetup.id } }">
            {{ formatDate(meetup.date) }} · {{ meetup.club.name }}
          </RouterLink>
          <span v-if="meetup.status === 'live'" class="user-card__live">идёт</span>
          <span v-if="meetup.disqualification" class="user-card__dq">
            Дисквалифицирован: {{ meetup.disqualification.reason }}
          </span>
          <span class="user-card__results">
            <RouterLink
              v-for="result in meetup.events"
              :key="result.event_id"
              class="user-card__result"
              :to="{ name: 'event-results', params: { meetupId: meetup.id, eventId: result.event_id } }"
            >
              {{ eventName(result.event_id) }}:
              <TimeValue
                :value="mainResult(result).value"
                :is-average="mainResult(result).isAverage"
                :result-type="EVENTS[result.event_id].resultType"
              />
              <RecordBadge v-for="mark in mainResult(result).marks" :key="mark" :mark="mark" />
              <span v-if="result.status === 'in_progress'" class="user-card__muted">(не завершена)</span>
            </RouterLink>
          </span>
        </li>
      </ul>
    </AppCard>

    <AppCard class="user-card__section">
      <h3 class="user-card__heading">Действия</h3>
      <div class="user-card__rows">
        <PasswordResetButton
          :user="{ id: user.id, display_name: user.display_name, login: user.login ?? '' }"
          :restriction="user.restrictions.reset_password"
        />
        <SettingRow
          title="Вернуть предыдущее имя"
          description="Отменяет последнюю смену имени. Ограничение пользователя на смену имени раз в 30 дней не сбрасывается."
          :restriction="user.restrictions.revert_name"
        >
          <AppButton variant="secondary" :disabled="user.restrictions.revert_name !== null" @click="askRevert">
            Вернуть имя
          </AppButton>
        </SettingRow>
        <SettingRow
          v-if="user.kept_name"
          title="Обезличить"
          description="Человек удалил аккаунт, но оставил имя в результатах. Если он отзывает согласие, имя заменится на «Удалённый участник»."
        >
          <AnonymizeButton :user="user" @anonymized="emit('changed')" />
        </SettingRow>
      </div>
    </AppCard>
  </div>

  <ConfirmDialog
    v-model:open="revertOpen"
    title="Вернуть предыдущее имя?"
    confirm-label="Вернуть имя"
    :loading="reverting"
    @confirm="revertName"
  >
    <p>Имя «{{ user.display_name }}» сменится на «{{ previousName }}» во всех таблицах.</p>
    <FormError v-if="revertError" :message="revertError" />
  </ConfirmDialog>
</template>

<style scoped>
.user-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.user-card__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.user-card__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  font-size: 18px;
  font-weight: var(--font-weight-heading);
  overflow-wrap: anywhere;
}

.user-card__heading {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.user-card__mark {
  padding: 0 var(--space-2);
  border: 1px solid currentColor;
  border-radius: var(--radius-badge);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-label);
  line-height: 18px;
}

.user-card__facts {
  display: grid;
  grid-template-columns: minmax(0, auto) minmax(0, 1fr);
  gap: var(--space-1) var(--space-3);
  margin: 0;
  font-size: var(--font-size-label);
}

.user-card__facts dt {
  color: var(--color-text-secondary);
}

.user-card__facts dd {
  margin: 0;
  overflow-wrap: anywhere;
}

.user-card__link {
  font-size: var(--font-size-label);
}

.user-card__muted {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.user-card__list,
.user-card__rows {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.user-card__list {
  gap: var(--space-2);
}

.user-card__list--divided {
  gap: 0;
}

.user-card__list--divided li + li,
.user-card__rows > * + * {
  border-top: 1px solid var(--color-border);
}

.user-card__club {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.user-card__meetup {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3) 0;
}

.user-card__meetup-title {
  font-weight: var(--font-weight-label);
  overflow-wrap: anywhere;
}

.user-card__live,
.user-card__dq {
  color: var(--color-danger);
  font-size: var(--font-size-label);
  overflow-wrap: anywhere;
}

.user-card__results {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  font-size: var(--font-size-label);
}

.user-card__result {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: inherit;
}
</style>
