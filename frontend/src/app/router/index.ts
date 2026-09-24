import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'
import { AuthPage } from '@/pages/auth'
import { ChangePasswordPage } from '@/pages/change-password'
import { ClubPage } from '@/pages/club'
import { ClubSettingsPage } from '@/pages/club-settings'
import { EventResultsPage } from '@/pages/event-results'
import { FmcPage } from '@/pages/fmc'
import { HomePage } from '@/pages/home'
import { JoinPage } from '@/pages/join'
import { MeetupPage } from '@/pages/meetup'
import { MeetupCreatePage } from '@/pages/meetup-create'
import { MeetupManagePage } from '@/pages/meetup-manage'
import { ProfilePage } from '@/pages/profile'
import { StatisticsPage } from '@/pages/statistics'
import { StubPage } from '@/pages/stub'
import { TimerPage } from '@/pages/timer'
import { installGuards } from './guards'

declare module 'vue-router' {
  interface RouteMeta {
    /** Только для вошедших: гостя отправляем на вход. */
    requiresAuth?: boolean
    /** Только для гостей: вошедшего отправляем дальше (вход, регистрация). */
    guestOnly?: boolean
    /** Какая вкладка навигации подсвечена. */
    tab?: 'club' | 'timer' | 'records' | 'statistics' | 'profile' | 'members'
  }
}

/** Числовые параметры адреса как props страницы: /clubs/5 → { clubId: 5 }. */
const numberParams = (...names: string[]) => (route: RouteLocationNormalized) =>
  Object.fromEntries(names.map((name) => [name, Number(route.params[name])]))

// Страницы без requiresAuth открыты всем, в том числе гостям.
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage, meta: { tab: 'club' } },
    { path: '/login', name: 'login', component: AuthPage, meta: { guestOnly: true } },
    { path: '/register', name: 'register', component: AuthPage, meta: { guestOnly: true } },
    {
      path: '/change-password',
      name: 'change-password',
      component: ChangePasswordPage,
      meta: { requiresAuth: true, tab: 'profile' },
    },

    // Клуб
    {
      path: '/clubs/:clubId(\\d+)',
      name: 'club',
      component: ClubPage,
      props: numberParams('clubId'),
      meta: { tab: 'club' },
    },
    {
      path: '/clubs/:clubId(\\d+)/settings',
      name: 'club-settings',
      component: ClubSettingsPage,
      props: numberParams('clubId'),
      meta: { requiresAuth: true, tab: 'club' },
    },
    {
      path: '/clubs/:clubId(\\d+)/meetups/new',
      name: 'meetup-create',
      component: MeetupCreatePage,
      props: numberParams('clubId'),
      meta: { requiresAuth: true, tab: 'club' },
    },
    {
      path: '/clubs/:clubId(\\d+)/records',
      name: 'club-records',
      component: StubPage,
      props: { title: 'Рекорды' },
      meta: { tab: 'records' },
    },
    {
      path: '/clubs/:clubId(\\d+)/members',
      name: 'club-members',
      component: StubPage,
      props: { title: 'Участники' },
      meta: { tab: 'members' },
    },

    // Встречи
    {
      path: '/meetups/:meetupId(\\d+)',
      name: 'meetup',
      component: MeetupPage,
      props: numberParams('meetupId'),
      meta: { tab: 'club' },
    },
    {
      path: '/meetups/:meetupId(\\d+)/manage',
      name: 'meetup-manage',
      component: MeetupManagePage,
      props: numberParams('meetupId'),
      meta: { requiresAuth: true, tab: 'club' },
    },
    {
      path: '/meetups/:meetupId(\\d+)/events/:eventId',
      name: 'event-results',
      component: EventResultsPage,
      props: (route) => ({ meetupId: Number(route.params.meetupId), eventId: route.params.eventId }),
      meta: { tab: 'club' },
    },
    { path: '/join/:token', name: 'join', component: JoinPage, props: true, meta: { tab: 'club' } },

    // Вкладки вошедшего пользователя
    {
      path: '/timer',
      name: 'timer',
      component: TimerPage,
      meta: { requiresAuth: true, tab: 'timer' },
    },
    {
      path: '/meetups/:meetupId(\\d+)/fmc',
      name: 'fmc',
      component: FmcPage,
      props: numberParams('meetupId'),
      meta: { requiresAuth: true, tab: 'timer' },
    },
    {
      path: '/statistics',
      name: 'statistics',
      component: StatisticsPage,
      meta: { requiresAuth: true, tab: 'statistics' },
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfilePage,
      meta: { requiresAuth: true, tab: 'profile' },
    },

    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

installGuards(router)
