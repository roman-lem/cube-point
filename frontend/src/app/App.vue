<script setup lang="ts">
import { AppNavigation } from '@/widgets/navigation'
</script>

<template>
  <div class="app">
    <AppNavigation />
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
