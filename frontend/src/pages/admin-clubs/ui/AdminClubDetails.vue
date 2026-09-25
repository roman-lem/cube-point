<script setup lang="ts">
import { ClubLogo, type AdminClub } from '@/entities/club'
import { ClubOrganizers } from '@/features/club-organizers'
import { plural } from '@/shared/lib'
import { AppCard, AppIcon } from '@/shared/ui'

// Управление клубом (макет admin_clubs_desk, правая панель).
const { club } = defineProps<{ club: AdminClub }>()
const emit = defineEmits<{ changed: [club: AdminClub] }>()
</script>

<template>
  <div class="admin-club">
    <AppCard class="admin-club__summary">
      <ClubLogo :name="club.name" :color="club.logo_color" :size="56" />
      <div class="admin-club__text">
        <h2 class="admin-club__name">{{ club.name }}</h2>
        <p class="admin-club__muted">{{ club.city }} · {{ club.timezone }}</p>
        <p class="admin-club__muted">
          {{ plural(club.members_count, ['участник', 'участника', 'участников']) }} ·
          {{ plural(club.meetups_count, ['встреча', 'встречи', 'встреч']) }}
        </p>
        <RouterLink :to="{ name: 'club', params: { clubId: club.id } }" class="admin-club__link">
          Открыть страницу клуба
          <AppIcon name="open-in-new" :size="16" />
        </RouterLink>
      </div>
    </AppCard>
    <ClubOrganizers :club="club" @changed="emit('changed', $event)" />
  </div>
</template>

<style scoped>
.admin-club {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.admin-club__summary {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
}

.admin-club__text {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.admin-club__name {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
  overflow-wrap: anywhere;
}

.admin-club__muted {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.admin-club__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  margin-top: var(--space-1);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}
</style>
