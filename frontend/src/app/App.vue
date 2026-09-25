<script setup lang="ts">
import { useRoute } from 'vue-router'
import { AppNavigation } from '@/widgets/navigation'

const route = useRoute()
</script>

<template>
  <div class="app">
    <!-- Страницы для печати — без навигации. -->
    <AppNavigation v-if="!route.meta.bare" />
    <RouterView />
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
</style>
