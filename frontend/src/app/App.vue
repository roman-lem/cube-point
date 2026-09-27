<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useCurrentClubStore } from '@/entities/club'
import { useUserStore } from '@/entities/user'
import { AppFooter } from '@/widgets/app-footer'
import { LandingHeader } from '@/widgets/landing-header'
import { AppNavigation } from '@/widgets/navigation'
import { useTimerStore } from '@/widgets/timer'

const route = useRoute()
const timerStore = useTimerStore()
const userStore = useUserStore()
const clubStore = useCurrentClubStore()
// The club tabs depend on who is logged in: tell the store once the user is known.
watch(
  () => (userStore.loaded ? (userStore.user?.id ?? null) : undefined),
  (id) => {
    if (id !== undefined) {
      clubStore.setUserId(id)
    }
  },
  { immediate: true },
)
// The timer and FMC use the whole screen as a touch area, so there is no footer.
const showFooter = computed(() => !route.meta.bare && route.meta.tab !== 'timer')
</script>

<template>
  <div class="app">
    <!-- The landing has its own header, print pages have no navigation. -->
    <LandingHeader v-if="route.meta.layout === 'landing'" />
    <!-- During inspection and a solve only the timer is on the screen. -->
    <AppNavigation v-else-if="!route.meta.bare && !timerStore.focused" />
    <RouterView />
    <AppFooter v-if="showFooter" :beta-note="route.meta.layout === 'landing'" />
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
</style>
