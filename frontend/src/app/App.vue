<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { AppFooter } from '@/widgets/app-footer'
import { LandingHeader } from '@/widgets/landing-header'
import { AppNavigation } from '@/widgets/navigation'

const route = useRoute()
// The timer and FMC use the whole screen as a touch area, so there is no footer.
const showFooter = computed(() => !route.meta.bare && route.meta.tab !== 'timer')
</script>

<template>
  <div class="app">
    <!-- The landing has its own header, print pages have no navigation. -->
    <LandingHeader v-if="route.meta.layout === 'landing'" />
    <AppNavigation v-else-if="!route.meta.bare" />
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
