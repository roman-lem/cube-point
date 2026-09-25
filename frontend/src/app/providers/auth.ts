import type { Router } from 'vue-router'
import { useUserStore } from '@/entities/user'
import { onConsentsRequired, onPasswordChangeRequired, onUnauthorized } from '@/shared/api'

/**
 * Реакция на ошибки авторизации из любого запроса.
 * Живёт в app: shared/api не может знать про store пользователя и роутер.
 */
export function setupAuthHandlers(router: Router) {
  const userStore = useUserStore()

  // Сессия закончилась или отозвана (сменили пароль на другом устройстве).
  onUnauthorized(() => {
    userStore.clear()
    const route = router.currentRoute.value
    if (route.meta.requiresAuth) {
      router.push({ name: 'login', query: { redirect: route.fullPath } })
    }
  })

  onPasswordChangeRequired(() => {
    userStore.requirePasswordChange()
    router.push({
      name: 'change-password',
      query: { redirect: router.currentRoute.value.fullPath },
    })
  })

  onConsentsRequired(() => {
    userStore.requireConsents()
    router.push({ name: 'consent', query: { redirect: router.currentRoute.value.fullPath } })
  })
}
