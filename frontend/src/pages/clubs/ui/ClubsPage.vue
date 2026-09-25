<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ClubCard, fetchClubs, type ClubSummary } from '@/entities/club'
import { AppCard, AppIcon, PageHeader } from '@/shared/ui'

// Все клубы с поиском по названию и городу. Карточки — как на лендинге.
const clubs = ref<ClubSummary[] | null>(null)
const failed = ref(false)
const query = ref('')

const visible = computed(() => {
  const text = query.value.trim().toLocaleLowerCase('ru')
  return (clubs.value ?? []).filter(
    (club) =>
      !text ||
      club.name.toLocaleLowerCase('ru').includes(text) ||
      club.city.toLocaleLowerCase('ru').includes(text),
  )
})

onMounted(async () => {
  try {
    clubs.value = await fetchClubs()
  } catch {
    failed.value = true
  }
})
</script>

<template>
  <main class="page clubs">
    <PageHeader title="Клубы" :back-to="{ name: 'home' }" />

    <AppCard v-if="failed">Не удалось загрузить клубы. Обновите страницу.</AppCard>

    <template v-else-if="clubs">
      <label class="clubs__search">
        <AppIcon name="search" :size="20" />
        <input v-model="query" type="search" placeholder="Название или город" aria-label="Поиск клуба" />
      </label>

      <div v-if="visible.length" class="clubs__grid">
        <ClubCard v-for="club in visible" :key="club.id" :club="club" />
      </div>
      <p v-else class="page__muted">
        {{ clubs.length ? 'Ничего не найдено' : 'Клубов пока нет' }}
      </p>
    </template>
  </main>
</template>

<style scoped>
.clubs__search {
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

.clubs__search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.clubs__search input {
  flex: 1;
  min-width: 0;
  background: none;
  border: none;
  color: var(--color-text-primary);
  outline: none;
}

.clubs__grid {
  display: grid;
  gap: var(--space-3);
}

@media (min-width: 768px) {
  .clubs__grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
