<script setup lang="ts">
import type { ClubMemberSummary, MemberFilter } from '@/entities/club'
import { MemberBadge } from '@/entities/club'
import { UserRow } from '@/entities/user'
import { plural } from '@/shared/lib'
import { AppIcon } from '@/shared/ui'

// Список участников клуба (макет org_club_competitors): поиск, у организатора —
// фильтры и переход к карточке участника, у остальных — к публичному профилю.
const query = defineModel<string>('query', { required: true })
const filter = defineModel<MemberFilter>('filter', { required: true })

const { clubId, members, canManage, filterCounts, selectedId } = defineProps<{
  clubId: number
  members: ClubMemberSummary[]
  canManage: boolean
  filterCounts?: Record<MemberFilter, number>
  /** Открытый участник — подсвечивается на широком экране. */
  selectedId?: number
}>()

const FILTERS: { value: MemberFilter; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'organizers', label: 'Организаторы' },
  { value: 'banned', label: 'Заблокированные' },
]

function details(member: ClubMemberSummary) {
  const parts = [plural(member.meetups_count, ['встреча', 'встречи', 'встреч'])]
  if (member.records_count) {
    parts.push(plural(member.records_count, ['рекорд клуба', 'рекорда клуба', 'рекордов клуба']))
  }
  return parts.join(' · ')
}
</script>

<template>
  <div class="member-list">
    <label class="member-list__search">
      <AppIcon name="search" :size="20" />
      <input
        v-model="query"
        type="search"
        :placeholder="canManage ? 'Имя или логин' : 'Имя'"
        aria-label="Поиск участника"
      />
      <button
        v-if="query"
        type="button"
        class="member-list__clear"
        aria-label="Очистить поиск"
        @click="query = ''"
      >
        <AppIcon name="close" :size="18" />
      </button>
    </label>

    <div v-if="canManage" class="member-list__filters" role="group" aria-label="Фильтр">
      <button
        v-for="item in FILTERS"
        :key="item.value"
        type="button"
        :aria-pressed="filter === item.value"
        :class="['member-list__chip', { 'member-list__chip--active': filter === item.value }]"
        @click="filter = item.value"
      >
        {{ item.label }}
        <span v-if="filterCounts" class="member-list__chip-count">{{ filterCounts[item.value] }}</span>
      </button>
    </div>

    <ul v-if="members.length" class="member-list__items">
      <li v-for="member in members" :key="member.user.id">
        <RouterLink
          v-if="canManage"
          :to="{ name: 'club-member', params: { clubId, userId: member.user.id } }"
          :class="['member-list__item', { 'member-list__item--active': member.user.id === selectedId }]"
        >
          <UserRow
            :display-name="member.user.display_name"
            :login="member.user.login"
            :details="details(member)"
          >
            <template #badges>
              <MemberBadge v-if="member.role === 'organizer'" kind="organizer" />
              <MemberBadge v-if="member.banned" kind="banned" />
            </template>
            <AppIcon name="chevron-right" :size="20" class="member-list__chevron" />
          </UserRow>
        </RouterLink>
        <RouterLink
          v-else
          :to="{ name: 'user-profile', params: { userId: member.user.id } }"
          class="member-list__item"
        >
          <UserRow :display-name="member.user.display_name" :details="details(member)">
            <template #badges>
              <MemberBadge v-if="member.role === 'organizer'" kind="organizer" />
            </template>
            <AppIcon name="chevron-right" :size="20" class="member-list__chevron" />
          </UserRow>
        </RouterLink>
      </li>
    </ul>
    <p v-else class="member-list__empty">
      {{ query ? `Никого не нашли. Проверьте ${canManage ? 'имя или логин' : 'имя'}.` : 'Здесь пока никого нет' }}
    </p>
  </div>
</template>

<style scoped>
.member-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.member-list__search {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: var(--control-height);
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  color: var(--color-text-secondary);
}

.member-list__search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.member-list__search input {
  flex: 1;
  min-width: 0;
  background: none;
  border: none;
  color: var(--color-text-primary);
  outline: none;
}

.member-list__clear {
  display: flex;
  padding: var(--space-1);
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
}

.member-list__filters {
  display: flex;
  gap: var(--space-2);
  overflow-x: auto;
}

.member-list__chip {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: var(--space-1);
  height: 36px;
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 18px;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.member-list__chip--active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-on-primary);
}

.member-list__chip-count {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.member-list__items {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  list-style: none;
  overflow: hidden;
}

.member-list__items li + li {
  border-top: 1px solid var(--color-border);
}

.member-list__item {
  display: block;
  padding: 0 var(--space-3);
  color: inherit;
  text-decoration: none;
}

.member-list__item--active {
  box-shadow: inset 3px 0 0 var(--color-primary);
  background: var(--color-background);
}

.member-list__chevron {
  flex-shrink: 0;
  color: var(--color-text-secondary);
}

.member-list__empty {
  padding: var(--space-5) 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  text-align: center;
}
</style>
