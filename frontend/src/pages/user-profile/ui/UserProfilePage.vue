<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TimeValue } from '@/entities/attempt'
import {
  fetchUserMeetups, fetchUserProfile, useUserStore, type ProfileMeetup, type UserProfile,
} from '@/entities/user'
import { ApiError } from '@/shared/api'
import { pluralForm } from '@/shared/lib'
import { AppButton, AppCard, AppIcon, PageHeader } from '@/shared/ui'
import MeetupHistoryCard from './MeetupHistoryCard.vue'
import PersonalRecordsTable from './PersonalRecordsTable.vue'

// Публичный профиль участника (макет personal_records): PB по всем клубам и история
// встреч с подгрузкой старых. Свой профиль — вкладка «Профиль», с кнопкой «Настройки».
const { userId } = defineProps<{ userId: number }>()

const userStore = useUserStore()
const profile = ref<UserProfile | null>(null)
const meetups = ref<ProfileMeetup[]>([])
const hasMore = ref(false)
const error = ref('')
const loadingMore = ref(false)
const moreError = ref('')

const isMe = computed(() => userStore.user?.id === userId)

watch(
  () => userId,
  async (id) => {
    profile.value = null
    meetups.value = []
    error.value = ''
    moreError.value = ''
    try {
      const [data, page] = await Promise.all([fetchUserProfile(id), fetchUserMeetups(id)])
      profile.value = data
      meetups.value = page.meetups
      hasMore.value = page.has_more
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить профиль'
    }
  },
  { immediate: true },
)

async function loadMore() {
  loadingMore.value = true
  moreError.value = ''
  try {
    const page = await fetchUserMeetups(userId, meetups.value.length)
    // Если за это время прошла новая встреча, страницы сдвинулись: повторы отбрасываем.
    const known = new Set(meetups.value.map((m) => m.id))
    meetups.value.push(...page.meetups.filter((m) => !known.has(m.id)))
    hasMore.value = page.has_more
  } catch (e) {
    moreError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить встречи'
  } finally {
    loadingMore.value = false
  }
}

const initials = computed(() =>
  (profile.value?.user.display_name ?? '')
    .split(' ')
    .slice(0, 2)
    .map((word) => word[0])
    .join(''),
)
const best333 = computed(
  () => profile.value?.personal_records.find((r) => r.event_id === '333')?.single ?? null,
)
</script>

<template>
  <main class="page page--narrow">
    <PageHeader
      :title="isMe ? 'Профиль' : 'Участник'"
      :back-to="isMe ? undefined : { name: 'home' }"
    >
      <template v-if="isMe" #action>
        <RouterLink class="user-profile__settings" :to="{ name: 'profile-settings' }">
          <AppIcon name="settings" :size="20" />
          Настройки
        </RouterLink>
      </template>
    </PageHeader>

    <AppCard v-if="error">{{ error }}</AppCard>

    <template v-else-if="profile">
      <AppCard class="user-profile__head">
        <div class="user-profile__who">
          <span class="user-profile__avatar" aria-hidden="true">{{ initials }}</span>
          <div>
            <h2 class="user-profile__name">{{ profile.user.display_name }}</h2>
            <p v-if="profile.clubs.length" class="user-profile__clubs">
              <AppIcon name="location" :size="16" />
              <template v-for="(club, i) in profile.clubs" :key="club.id">
                <template v-if="i > 0">, </template>
                <RouterLink :to="{ name: 'club', params: { clubId: club.id } }">{{ club.name }}</RouterLink>
              </template>
            </p>
          </div>
        </div>
        <dl class="user-profile__stats">
          <div>
            <dt>{{ pluralForm(profile.meetups_count, ['встреча', 'встречи', 'встреч']) }}</dt>
            <dd>{{ profile.meetups_count }}</dd>
          </div>
          <div>
            <dt>{{ pluralForm(profile.personal_records.length, ['дисциплина', 'дисциплины', 'дисциплин']) }}</dt>
            <dd>{{ profile.personal_records.length }}</dd>
          </div>
          <div v-if="best333">
            <dt>лучшая 3x3</dt>
            <dd><TimeValue :value="best333.value" /></dd>
          </div>
        </dl>
      </AppCard>

      <section class="page__section">
        <h2 class="page__section-title">Личные рекорды</h2>
        <PersonalRecordsTable v-if="profile.personal_records.length" :records="profile.personal_records" />
        <p v-else class="page__muted">Результатов на встречах пока нет</p>
      </section>

      <section v-if="meetups.length" class="page__section">
        <h2 class="page__section-title">История встреч</h2>
        <MeetupHistoryCard
          v-for="meetup in meetups"
          :key="meetup.id"
          :meetup="meetup"
          :show-club="profile.clubs.length > 1"
        />
        <p v-if="moreError" class="page__muted">{{ moreError }}</p>
        <AppButton v-if="hasMore" variant="secondary" :loading="loadingMore" @click="loadMore">
          Показать ещё
        </AppButton>
      </section>
    </template>
  </main>
</template>

<style scoped>
.user-profile__settings {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.user-profile__head {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.user-profile__who {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.user-profile__avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  background: var(--color-primary);
  border-radius: 50%;
  color: var(--color-on-primary);
  font-size: 20px;
  font-weight: var(--font-weight-heading);
}

.user-profile__name {
  font-size: var(--font-size-heading);
  font-weight: var(--font-weight-heading);
}

.user-profile__clubs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0 var(--space-1);
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.user-profile__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
  margin: 0;
}

.user-profile__stats > div {
  display: flex;
  flex-direction: column-reverse;
  align-items: center;
  padding: var(--space-2);
  background: var(--color-background);
  border-radius: var(--radius-button);
}

.user-profile__stats dt {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.user-profile__stats dd {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--font-size-time-large);
  font-weight: var(--font-weight-time-large);
  font-variant-numeric: tabular-nums;
}
</style>
