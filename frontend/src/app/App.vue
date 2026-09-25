<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { AppFooter } from '@/widgets/app-footer'
import { AppNavigation } from '@/widgets/navigation'

const route = useRoute()
// Таймер и FMC занимают весь экран под зону касания, там подвала нет.
const showFooter = computed(() => !route.meta.bare && route.meta.tab !== 'timer')
</script>

<template>
  <div class="app">
    <!-- Страницы для печати — без навигации. -->
    <AppNavigation v-if="!route.meta.bare" />
    <RouterView />
    <AppFooter v-if="showFooter" />
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
</style>
