import type { Router } from 'vue-router'
import { useUserStore } from '@/entities/user'
import { safeRedirect } from '@/shared/lib'

export function installGuards(router: Router) {
  router.beforeEach(async (to) => {
    const userStore = useUserStore()
    // Первая навигация ждёт /api/auth/me, дальше пользователь уже в store.
    await userStore.ensureLoaded()
    const user = userStore.user

    // Временный пароль: пока не сменён, доступна только смена пароля.
    if (user?.must_change_password && to.name !== 'change-password') {
      return { name: 'change-password', query: { redirect: to.fullPath } }
    }
    // Нет согласий (аккаунт от организатора или обновился текст): пока их не дать,
    // доступны только страница согласия и сам текст политики.
    if (
      user?.consents_required && !user.must_change_password &&
      to.name !== 'consent' && to.name !== 'privacy'
    ) {
      return { name: 'consent', query: { redirect: to.fullPath } }
    }
    if (to.meta.requiresAuth && !user) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    // Права проверяет сервер, здесь только не открываем страницу, которая не загрузится.
    if (to.meta.requiresAdmin && !user?.is_admin) {
      return { name: 'home' }
    }
    if (to.meta.guestOnly && user) {
      return safeRedirect(to.query.redirect)
    }
    return true
  })
}
