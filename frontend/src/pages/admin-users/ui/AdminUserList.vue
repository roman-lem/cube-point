<script setup lang="ts">
import { MemberBadge } from '@/entities/club'
import { UserRow } from '@/entities/user'
import { formatDate } from '@/shared/lib'
import { AppIcon } from '@/shared/ui'
import type { AdminUser, UserFilter } from '../api/adminUsersApi'

// User list: search by name, login and email, filters, "Show more".
const query = defineModel<string>('query', { required: true })
const filter = defineModel<UserFilter>('filter', { required: true })

const { users, hasMore, loadingMore, selectedId } = defineProps<{
  users: AdminUser[]
  hasMore: boolean
  loadingMore: boolean
  /** The open user is highlighted on a wide screen. */
  selectedId?: number
}>()
const emit = defineEmits<{ more: [] }>()

const FILTERS: { value: UserFilter; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'admins', label: 'Администраторы' },
  { value: 'organizers', label: 'Организаторы' },
  { value: 'deleted', label: 'Удалённые' },
]

function details(user: AdminUser) {
  const parts = [user.email, `с ${formatDate(user.created_at.slice(0, 10))}`]
  return parts.filter(Boolean).join(' · ')
}
</script>

<template>
  <div class="user-list">
    <label class="user-list__search">
      <AppIcon name="search" :size="20" />
      <input
        v-model="query"
        type="search"
        placeholder="Имя, логин или почта"
        aria-label="Поиск пользователя"
      />
      <button
        v-if="query"
        type="button"
        class="user-list__clear"
        aria-label="Очистить поиск"
        @click="query = ''"
      >
        <AppIcon name="close" :size="18" />
      </button>
    </label>

    <div class="user-list__filters" role="group" aria-label="Фильтр">
      <button
        v-for="item in FILTERS"
        :key="item.value"
        type="button"
        :aria-pressed="filter === item.value"
        :class="['user-list__chip', { 'user-list__chip--active': filter === item.value }]"
        @click="filter = item.value"
      >
        {{ item.label }}
      </button>
    </div>

    <ul v-if="users.length" class="user-list__items">
      <li v-for="user in users" :key="user.id">
        <RouterLink
          :to="{ name: 'admin-user', params: { userId: user.id } }"
          :class="['user-list__item', { 'user-list__item--active': user.id === selectedId }]"
        >
          <UserRow
            :display-name="user.display_name"
            :login="user.login ?? undefined"
            :details="details(user)"
          >
            <template #badges>
              <span v-if="user.is_admin" class="user-list__mark">Админ</span>
              <span v-if="user.deleted_at" class="user-list__mark user-list__mark--deleted">
                Удалён
              </span>
            </template>
            <AppIcon name="chevron-right" :size="20" class="user-list__chevron" />
          </UserRow>
          <span v-if="user.clubs.length" class="user-list__clubs">
            <span v-for="club in user.clubs" :key="club.id" class="user-list__club">
              {{ club.name }}
              <MemberBadge v-if="club.role === 'organizer'" kind="organizer" />
              <MemberBadge v-if="club.banned" kind="banned" />
            </span>
          </span>
        </RouterLink>
      </li>
    </ul>
    <p v-else class="user-list__empty">Никого не нашлось</p>

    <button
      v-if="hasMore"
      type="button"
      class="user-list__more"
      :disabled="loadingMore"
      @click="emit('more')"
    >
      {{ loadingMore ? 'Загрузка…' : 'Показать ещё' }}
    </button>
  </div>
</template>

<style scoped>
.user-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.user-list__search {
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

.user-list__search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.user-list__search input {
  flex: 1;
  min-width: 0;
  background: none;
  border: none;
  color: var(--color-text-primary);
  outline: none;
}

.user-list__clear {
  display: flex;
  padding: var(--space-1);
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
}

.user-list__filters {
  display: flex;
  gap: var(--space-2);
  overflow-x: auto;
}

.user-list__chip {
  flex-shrink: 0;
  height: 36px;
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 18px;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.user-list__chip--active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-on-primary);
}

.user-list__items {
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

.user-list__items li + li {
  border-top: 1px solid var(--color-border);
}

.user-list__item {
  display: flex;
  flex-direction: column;
  padding: var(--space-1) var(--space-3) var(--space-2);
  color: inherit;
  text-decoration: none;
}

.user-list__item--active {
  background: color-mix(in srgb, var(--color-primary) 6%, var(--color-surface));
}

.user-list__mark {
  padding: 0 var(--space-2);
  border: 1px solid currentColor;
  border-radius: var(--radius-badge);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-label);
  line-height: 18px;
}

.user-list__mark--deleted {
  color: var(--color-danger);
}

.user-list__clubs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  padding-left: 52px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.user-list__club {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.user-list__chevron {
  flex-shrink: 0;
  margin-left: auto;
  color: var(--color-text-secondary);
}

.user-list__empty {
  padding: var(--space-5) 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  text-align: center;
}

.user-list__more {
  align-self: center;
  height: var(--control-height);
  padding: 0 var(--space-4);
  background: none;
  border: none;
  color: var(--color-primary);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}
</style>
