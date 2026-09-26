<script setup lang="ts">
import { computed, ref } from 'vue'
import { ClubLogo, type AdminClubSummary } from '@/entities/club'
import { formatDate, plural } from '@/shared/lib'
import { AppIcon } from '@/shared/ui'

// Club list with search by name and city.
const { clubs, selectedId } = defineProps<{
  clubs: AdminClubSummary[]
  /** The open club is highlighted on a wide screen. */
  selectedId?: number
}>()

const query = ref('')

const visible = computed(() => {
  const text = query.value.trim().toLocaleLowerCase('ru')
  return clubs.filter(
    (club) =>
      !text ||
      club.name.toLocaleLowerCase('ru').includes(text) ||
      club.city.toLocaleLowerCase('ru').includes(text),
  )
})
</script>

<template>
  <div class="admin-club-list">
    <label class="admin-club-list__search">
      <AppIcon name="search" :size="20" />
      <input v-model="query" type="search" placeholder="Название или город" aria-label="Поиск клуба" />
      <button
        v-if="query"
        type="button"
        class="admin-club-list__clear"
        aria-label="Очистить поиск"
        @click="query = ''"
      >
        <AppIcon name="close" :size="18" />
      </button>
    </label>

    <ul class="admin-club-list__items">
      <li v-for="club in visible" :key="club.id">
        <RouterLink
          :to="{ name: 'admin-club', params: { clubId: club.id } }"
          :class="['admin-club-list__item', { 'admin-club-list__item--active': club.id === selectedId }]"
        >
          <ClubLogo :name="club.name" :color="club.logo_color" :size="40" />
          <span class="admin-club-list__text">
            <span class="admin-club-list__name">{{ club.name }}</span>
            <span class="admin-club-list__muted">
              {{ club.city }} · {{ plural(club.members_count, ['участник', 'участника', 'участников']) }}
              · {{ club.organizers_count }} орг.
            </span>
            <span class="admin-club-list__muted">
              {{
                club.last_meetup_date
                  ? `Последняя встреча: ${formatDate(club.last_meetup_date)}`
                  : 'Встреч ещё не было'
              }}
            </span>
          </span>
          <AppIcon name="chevron-right" :size="20" class="admin-club-list__chevron" />
        </RouterLink>
      </li>
    </ul>

    <p v-if="visible.length === 0" class="admin-club-list__empty">
      {{ clubs.length ? 'Клубы не найдены. Проверьте название или город.' : 'Клубов пока нет' }}
    </p>
  </div>
</template>

<style scoped>
.admin-club-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.admin-club-list__search {
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

.admin-club-list__search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.admin-club-list__search input {
  flex: 1;
  min-width: 0;
  background: none;
  border: none;
  color: var(--color-text-primary);
  outline: none;
}

.admin-club-list__clear {
  display: flex;
  padding: var(--space-1);
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
}

.admin-club-list__items {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.admin-club-list__item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: inherit;
  text-decoration: none;
}

.admin-club-list__item--active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.admin-club-list__text {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.admin-club-list__name {
  font-weight: var(--font-weight-label);
  overflow-wrap: anywhere;
}

.admin-club-list__muted,
.admin-club-list__empty {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.admin-club-list__chevron {
  flex-shrink: 0;
  color: var(--color-text-secondary);
}

.admin-club-list__empty {
  padding: var(--space-5) 0;
  text-align: center;
}
</style>
