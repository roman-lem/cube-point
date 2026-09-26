<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import { computed, onMounted } from 'vue'
import { useRoute, type RouteLocationRaw } from 'vue-router'
import { useCurrentClubStore } from '@/entities/club'
import { useUserStore } from '@/entities/user'
import { SITE_NAME } from '@/shared/config'
import { AppIcon, LiveIndicator, type IconName } from '@/shared/ui'

// Navigation as described in "Navigation" in docs/ARCHITECTURE.md:
// a bottom bar on mobile, a top bar on desktop.
const route = useRoute()
const userStore = useUserStore()
const clubStore = useCurrentClubStore()
const isDesktop = useMediaQuery('(min-width: 768px)')

onMounted(() => clubStore.load())

interface NavItem {
  tab: NonNullable<typeof route.meta.tab>
  label: string
  icon: IconName
  to: RouteLocationRaw
}

const items = computed<NavItem[]>(() => {
  const clubId = clubStore.clubId
  // While the club is unknown, the club tabs lead home: it picks the club itself.
  const clubRoute = (name: string): RouteLocationRaw =>
    clubId ? { name, params: { clubId } } : { name: 'home' }

  const club: NavItem = { tab: 'club', label: 'Клуб', icon: 'home', to: clubRoute('club') }
  const records: NavItem = {
    tab: 'records', label: 'Рекорды', icon: 'trophy', to: clubRoute('club-records'),
  }

  if (!userStore.user) {
    return [
      club,
      records,
      { tab: 'members', label: 'Участники', icon: 'group', to: clubRoute('club-members') },
    ]
  }
  return [
    club,
    { tab: 'timer', label: 'Таймер', icon: 'timer', to: { name: 'timer' } },
    records,
    { tab: 'statistics', label: 'Статистика', icon: 'bar-chart', to: { name: 'statistics' } },
    { tab: 'profile', label: 'Профиль', icon: 'account', to: { name: 'profile' } },
  ]
})

// One's own public profile opened via a link from tables is also the "Profile" tab.
const activeTab = computed(() =>
  route.name === 'user-profile' && Number(route.params.userId) === userStore.user?.id
    ? 'profile'
    : route.meta.tab,
)

// "Log in" is not needed on the login and registration pages themselves.
const showLogin = computed(
  () => !userStore.user && route.name !== 'login' && route.name !== 'register',
)
const loginRoute = computed(() => ({ name: 'login', query: { redirect: route.fullPath } }))
</script>

<template>
  <header v-if="isDesktop" class="top-nav">
    <div class="top-nav__inner">
      <span class="top-nav__brand">{{ clubStore.club?.name ?? SITE_NAME }}</span>
      <nav class="top-nav__items" aria-label="Основная навигация">
        <RouterLink
          v-for="item in items"
          :key="item.tab"
          :to="item.to"
          :class="['top-nav__item', { 'top-nav__item--active': activeTab === item.tab }]"
        >
          {{ item.label }}
          <LiveIndicator v-if="item.tab === 'club' && clubStore.isLive" />
        </RouterLink>
      </nav>
      <RouterLink v-if="showLogin" :to="loginRoute" class="top-nav__login">
        <AppIcon name="login" :size="20" />
        Войти
      </RouterLink>
    </div>
  </header>

  <template v-else>
    <header v-if="showLogin" class="mobile-header">
      <span class="top-nav__brand">{{ clubStore.club?.name ?? SITE_NAME }}</span>
      <RouterLink :to="loginRoute" class="top-nav__login">
        <AppIcon name="login" :size="20" />
        Войти
      </RouterLink>
    </header>
    <!-- Space for the fixed bar so it does not cover the end of the page. -->
    <div class="bottom-nav__spacer" aria-hidden="true" />
    <nav class="bottom-nav" aria-label="Основная навигация">
      <RouterLink
        v-for="item in items"
        :key="item.tab"
        :to="item.to"
        :class="['bottom-nav__item', { 'bottom-nav__item--active': activeTab === item.tab }]"
      >
        <span class="bottom-nav__icon">
          <AppIcon :name="item.icon" />
          <span
            v-if="item.tab === 'club' && clubStore.isLive"
            class="bottom-nav__live"
            aria-label="Идёт встреча"
          />
        </span>
        {{ item.label }}
      </RouterLink>
    </nav>
  </template>
</template>

<style scoped>
.top-nav {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.top-nav__inner {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  max-width: var(--content-max-width);
  height: 64px;
  margin: 0 auto;
  padding: 0 var(--page-padding);
}

.top-nav__brand {
  overflow: hidden;
  font-weight: var(--font-weight-heading);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-nav__items {
  display: flex;
  flex: 1;
  justify-content: center;
  gap: var(--space-1);
}

.top-nav__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 40px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-button);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.top-nav__item:hover {
  background: var(--color-background);
}

.top-nav__item--active {
  background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface));
  color: var(--color-primary);
}

.top-nav__login {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: var(--space-2);
  height: 40px;
  padding: 0 var(--space-4);
  background: var(--color-primary);
  border-radius: var(--radius-button);
  color: var(--color-on-primary);
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.mobile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  height: 56px;
  padding: 0 var(--page-padding);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.bottom-nav__spacer {
  order: 99;
  height: calc(64px + env(safe-area-inset-bottom, 0px));
}

.bottom-nav {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 10;
  display: flex;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
}

.bottom-nav__item {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  height: 64px;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.bottom-nav__item--active {
  color: var(--color-primary);
}

.bottom-nav__icon {
  position: relative;
  display: flex;
}

.bottom-nav__live {
  position: absolute;
  top: -2px;
  right: -6px;
  width: 8px;
  height: 8px;
  border: 2px solid var(--color-surface);
  border-radius: 50%;
  background: var(--color-primary);
  box-sizing: content-box;
}
</style>
