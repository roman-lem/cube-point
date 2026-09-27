<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { ClubLogo, useCurrentClubStore } from '@/entities/club'
import { AppIcon } from '@/shared/ui'

// "My clubs" in one's own profile: clubs the user is a member of (without the ones
// they are banned in: there my_role is null) and a link to all clubs.
const clubStore = useCurrentClubStore()

// Fresh list: the user may have joined a club since the app was opened.
onMounted(() => clubStore.load(true))

const myClubs = computed(() => clubStore.clubs.filter((club) => club.my_role))
</script>

<template>
  <section class="page__section">
    <h2 class="page__section-title">Мои клубы</h2>
    <ul v-if="myClubs.length" class="my-clubs">
      <li v-for="club in myClubs" :key="club.id">
        <RouterLink :to="{ name: 'club', params: { clubId: club.id } }" class="my-clubs__item">
          <ClubLogo :name="club.name" :color="club.logo_color" :size="40" />
          <span class="my-clubs__text">
            <span class="my-clubs__name">{{ club.name }}</span>
            <span class="my-clubs__muted">
              {{ club.city }} · {{ club.my_role === 'organizer' ? 'Организатор' : 'Участник' }}
            </span>
          </span>
          <AppIcon name="chevron-right" :size="20" class="my-clubs__chevron" />
        </RouterLink>
      </li>
    </ul>
    <p v-else-if="clubStore.loaded" class="page__muted">Вы пока не состоите ни в одном клубе</p>
    <RouterLink :to="{ name: 'clubs' }" class="my-clubs__all">
      Все клубы
      <AppIcon name="arrow-forward" :size="18" />
    </RouterLink>
  </section>
</template>

<style scoped>
.my-clubs {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.my-clubs__item {
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

.my-clubs__item:hover {
  border-color: var(--color-primary);
}

.my-clubs__text {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.my-clubs__name {
  font-weight: var(--font-weight-label);
  overflow-wrap: anywhere;
}

.my-clubs__muted {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.my-clubs__chevron {
  flex-shrink: 0;
  color: var(--color-text-secondary);
}

.my-clubs__all {
  display: inline-flex;
  align-self: flex-start;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  text-decoration: none;
}
</style>
