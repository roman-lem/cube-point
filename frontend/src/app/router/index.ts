import { createRouter, createWebHistory } from 'vue-router'
import { AuthPage } from '@/pages/auth'
import { ChangePasswordPage } from '@/pages/change-password'
import { HomePage } from '@/pages/home'
import { installGuards } from './guards'

declare module 'vue-router' {
  interface RouteMeta {
    /** Только для вошедших: гостя отправляем на вход. */
    requiresAuth?: boolean
    /** Только для гостей: вошедшего отправляем дальше (вход, регистрация). */
    guestOnly?: boolean
  }
}

// Страницы без меток открыты всем, в том числе гостям.
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/login', name: 'login', component: AuthPage, meta: { guestOnly: true } },
    { path: '/register', name: 'register', component: AuthPage, meta: { guestOnly: true } },
    {
      path: '/change-password',
      name: 'change-password',
      component: ChangePasswordPage,
      meta: { requiresAuth: true },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

installGuards(router)
