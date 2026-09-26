<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ClubCard, fetchClubs, type ClubSummary } from '@/entities/club'
import { useUserStore } from '@/entities/user'
import { DEVELOPER_CONTACTS, SITE_NAME } from '@/shared/config'
import { AppButton, AppIcon, StepList, type IconName, type Step } from '@/shared/ui'

// Landing at the site root. It is seen by guests
// and logged-in users without a club; those with a club are redirected to the club page by the router.
const userStore = useUserStore()

const HOW_IT_WORKS: Step[] = [
  { title: 'Организатор создаёт встречу', text: 'Выбирает дату, место и дисциплины.' },
  {
    title: 'Участники заходят по QR-коду или ссылке',
    text: 'Организатор подтверждает, что участник пришёл на встречу.',
  },
  {
    title: 'Результаты сразу попадают в таблицу встречи',
    text: 'Средние и рекорды клуба считаются автоматически.',
  },
]

const NEW_CLUB: Step[] = [
  { title: 'Зарегистрируйтесь на сайте' },
  { title: 'Напишите разработчику: город, название клуба и ваш логин' },
  { title: 'После уточнения деталей клуб будет создан, а вы станете его организатором' },
  { title: 'Настройте страницу клуба и проведите первую встречу' },
]

const CONTACTS: { label: string; icon: IconName; href: string }[] = [
  { label: 'Почта', icon: 'mail', href: `mailto:${DEVELOPER_CONTACTS.email}` },
  { label: 'Telegram', icon: 'send', href: DEVELOPER_CONTACTS.telegram },
  { label: 'ВКонтакте', icon: 'forum', href: DEVELOPER_CONTACTS.vk },
]

// The server returns clubs with the most recent meetups first.
const clubs = ref<ClubSummary[]>([])
const recentClubs = computed(() => clubs.value.slice(0, 3))

onMounted(async () => {
  try {
    clubs.value = await fetchClubs()
  } catch {
    // The landing is useful even without the club list; the section is just hidden.
  }
})
</script>

<template>
  <main class="page landing">
    <section class="landing__hero">
      <h1 class="landing__title">{{ SITE_NAME }} спидкуберов твоего города</h1>
      <p class="landing__lead">
        Встречи, мини-соревнования, живые таблицы результатов и рекорды для локальных клубов
      </p>
      <p v-if="userStore.user" class="landing__signed-in">
        Вы вошли как {{ userStore.user.display_name }}. Клуб появится в вашем профиле после
        первой встречи — попросите организатора показать QR-код
      </p>
      <div v-else class="landing__actions">
        <AppButton :to="{ name: 'register' }">Зарегистрироваться</AppButton>
        <AppButton variant="secondary" :to="{ name: 'login' }">Войти</AppButton>
      </div>
    </section>

    <section class="page__section">
      <h2 class="page__section-title">Для кого</h2>
      <div class="landing__grid landing__grid--two">
        <article class="landing__card">
          <h3 class="landing__card-title">Участникам</h3>
          <p class="page__muted">
            Решайте головоломки на встречах, засекая время на своём телефоне, следите за
            личными рекордами и прогрессом, сравнивайте результаты с клубом.
          </p>
        </article>
        <article class="landing__card">
          <h3 class="landing__card-title">Организаторам</h3>
          <p class="page__muted">
            Встреча создаётся за минуту и проходит без бумажных бланков — результаты сразу
            собираются в одну таблицу, а рекорды клуба обновляются сами.
          </p>
        </article>
      </div>
    </section>

    <section class="page__section">
      <h2 class="page__section-title">Как это работает</h2>
      <StepList :steps="HOW_IT_WORKS" />
    </section>

    <section class="landing__join">
      <h2 class="page__section-title">Как вступить в клуб</h2>
      <p>
        Вступить в клуб можно только на встрече: организатор покажет QR-код или даст ссылку,
        по которой вы присоединитесь. Зарегистрироваться можно заранее — клуб появится в вашем
        профиле после первой встречи.
      </p>
    </section>

    <section v-if="recentClubs.length" class="page__section">
      <h2 class="page__section-title">Клубы</h2>
      <div class="landing__grid landing__grid--three">
        <ClubCard v-for="club in recentClubs" :key="club.id" :club="club" />
      </div>
      <RouterLink :to="{ name: 'clubs' }" class="landing__more">
        Все клубы
        <AppIcon name="arrow-forward" :size="18" />
      </RouterLink>
    </section>

    <section class="page__section">
      <h2 class="page__section-title">Нет клуба в вашем городе?</h2>
      <StepList :steps="NEW_CLUB" />
      <h3 class="landing__contacts-title">Связаться с разработчиком</h3>
      <div class="landing__contacts">
        <a
          v-for="contact in CONTACTS"
          :key="contact.label"
          :href="contact.href"
          target="_blank"
          rel="noopener"
          class="landing__contact"
        >
          <AppIcon :name="contact.icon" :size="20" />
          {{ contact.label }}
        </a>
      </div>
    </section>
  </main>
</template>

<style scoped>
.landing {
  gap: var(--space-6);
}

.landing__hero {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-top: var(--space-2);
}

.landing__title {
  font-size: 28px;
  font-weight: var(--font-weight-heading);
  line-height: 1.2;
}

.landing__lead {
  color: var(--color-text-secondary);
}

.landing__actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.landing__signed-in {
  margin-top: var(--space-2);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}

.landing__grid {
  display: grid;
  gap: var(--space-3);
}

.landing__card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}

.landing__card-title {
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-label);
}

.landing__join {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  background: color-mix(in srgb, var(--color-primary) 6%, var(--color-surface));
  border: 1px solid color-mix(in srgb, var(--color-primary) 20%, var(--color-surface));
  border-radius: var(--radius-card);
}

.landing__more {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  align-self: flex-start;
  color: var(--color-primary);
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.landing__contacts-title {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.landing__contacts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
}

.landing__contact {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  padding: var(--space-3) var(--space-2);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  color: var(--color-text-primary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.landing__contact:hover {
  border-color: var(--color-primary);
}

@media (min-width: 768px) {
  .landing__hero {
    max-width: 680px;
    padding-top: var(--space-6);
  }

  .landing__title {
    font-size: 40px;
  }

  .landing__actions {
    flex-direction: row;
  }

  .landing__grid--two {
    grid-template-columns: repeat(2, 1fr);
  }

  .landing__grid--three {
    grid-template-columns: repeat(3, 1fr);
  }

  .landing__contacts {
    display: flex;
    flex-wrap: wrap;
  }

  .landing__contact {
    flex-direction: row;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
  }
}
</style>
