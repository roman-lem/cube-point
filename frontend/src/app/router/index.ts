import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'
import { fetchHomeClubId } from '@/entities/club'
import { useUserStore } from '@/entities/user'
import { AdminClubCreatePage } from '@/pages/admin-club-create'
import { AdminClubsPage } from '@/pages/admin-clubs'
import { AdminDeletedUsersPage } from '@/pages/admin-deleted-users'
import { AuthPage } from '@/pages/auth'
import { ChangePasswordPage } from '@/pages/change-password'
import { ClubPage } from '@/pages/club'
import { ClubRecordsPage } from '@/pages/club-records'
import { ClubsPage } from '@/pages/clubs'
import { ClubMembersPage } from '@/pages/club-members'
import { ClubSettingsPage } from '@/pages/club-settings'
import { ConsentPage } from '@/pages/consent'
import { EventResultsPage } from '@/pages/event-results'
import { FmcPage } from '@/pages/fmc'
import { JoinPage } from '@/pages/join'
import { LandingPage } from '@/pages/landing'
import { MeetupPage } from '@/pages/meetup'
import { MeetupCreatePage } from '@/pages/meetup-create'
import { MeetupManagePage } from '@/pages/meetup-manage'
import { PrivacyPage } from '@/pages/privacy'
import { ProfileSettingsPage } from '@/pages/profile-settings'
import { PublicationConsentPage } from '@/pages/publication-consent'
import { ScramblePrintPage } from '@/pages/scramble-print'
import { SeriesEditPage } from '@/pages/series-edit'
import { StatisticsPage } from '@/pages/statistics'
import { TimerPage } from '@/pages/timer'
import { UserProfilePage } from '@/pages/user-profile'
import { installGuards } from './guards'

declare module 'vue-router' {
  interface RouteMeta {
    /** Только для вошедших: гостя отправляем на вход. */
    requiresAuth?: boolean
    /** Только для администратора: остальных отправляем на главную. */
    requiresAdmin?: boolean
    /** Только для гостей: вошедшего отправляем дальше (вход, регистрация). */
    guestOnly?: boolean
    /** Страница без навигации (печать). */
    bare?: boolean
    /** Раскладка лендинга: своя шапка вместо вкладок приложения. */
    layout?: 'landing'
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
  // Ссылки на разделы страницы (/privacy#processing) прокручивают к ним.
  scrollBehavior(to, _from, savedPosition) {
    if (to.hash) {
      return { el: to.hash }
    }
    return savedPosition ?? false
  },
  routes: [
    // Корень сайта: вошедшего с клубом — в клуб его последней встречи,
    // гостя и вошедшего без клуба — на лендинг.
    {
      path: '/',
      name: 'home',
      component: LandingPage,
      meta: { layout: 'landing' },
      beforeEnter: async () => {
        if (!useUserStore().user) {
          return true
        }
        try {
          const clubId = await fetchHomeClubId()
          return clubId ? { name: 'club', params: { clubId } } : true
        } catch {
          return true
        }
      },
    },
    { path: '/clubs', name: 'clubs', component: ClubsPage, meta: { layout: 'landing' } },
    { path: '/login', name: 'login', component: AuthPage, meta: { guestOnly: true } },
    { path: '/register', name: 'register', component: AuthPage, meta: { guestOnly: true } },
    { path: '/privacy', name: 'privacy', component: PrivacyPage },
    {
      path: '/publication-consent',
      name: 'publication-consent',
      component: PublicationConsentPage,
    },
    {
      path: '/consent',
      name: 'consent',
      component: ConsentPage,
      meta: { requiresAuth: true, tab: 'profile' },
    },
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
      component: ClubRecordsPage,
      props: numberParams('clubId'),
      meta: { tab: 'records' },
    },
    {
      path: '/clubs/:clubId(\\d+)/members',
      name: 'club-members',
      component: ClubMembersPage,
      props: numberParams('clubId'),
      meta: { tab: 'members' },
    },
    {
      path: '/clubs/:clubId(\\d+)/members/:userId(\\d+)',
      name: 'club-member',
      component: ClubMembersPage,
      props: numberParams('clubId', 'userId'),
      meta: { requiresAuth: true, tab: 'members' },
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
      path: '/meetups/:meetupId(\\d+)/participants/:userId(\\d+)',
      name: 'series-edit',
      component: SeriesEditPage,
      props: numberParams('meetupId', 'userId'),
      meta: { requiresAuth: true, tab: 'club' },
    },
    {
      path: '/meetups/:meetupId(\\d+)/print',
      name: 'scramble-print',
      component: ScramblePrintPage,
      props: numberParams('meetupId'),
      meta: { requiresAuth: true, bare: true },
    },
    {
      path: '/meetups/:meetupId(\\d+)/events/:eventId',
      name: 'event-results',
      component: EventResultsPage,
      props: (route) => ({ meetupId: Number(route.params.meetupId), eventId: route.params.eventId }),
      meta: { tab: 'club' },
    },
    { path: '/join/:token', name: 'join', component: JoinPage, props: true, meta: { tab: 'club' } },

    // Публичный профиль участника. Свой подсвечивает вкладку «Профиль» (см. AppNavigation).
    {
      path: '/users/:userId(\\d+)',
      name: 'user-profile',
      component: UserProfilePage,
      props: numberParams('userId'),
      meta: { tab: 'members' },
    },

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
    // Вкладка «Профиль» — свой публичный профиль (requiresAuth: пользователь уже загружен).
    {
      path: '/profile',
      name: 'profile',
      component: UserProfilePage,
      props: () => ({ userId: useUserStore().user?.id }),
      meta: { requiresAuth: true, tab: 'profile' },
    },
    {
      path: '/profile/settings',
      name: 'profile-settings',
      component: ProfileSettingsPage,
      meta: { requiresAuth: true, tab: 'profile' },
    },

    // Администрирование (пункт во вкладке «Профиль»)
    {
      path: '/admin/clubs',
      name: 'admin-clubs',
      component: AdminClubsPage,
      meta: { requiresAuth: true, requiresAdmin: true, tab: 'profile' },
    },
    {
      path: '/admin/clubs/new',
      name: 'admin-club-create',
      component: AdminClubCreatePage,
      meta: { requiresAuth: true, requiresAdmin: true, tab: 'profile' },
    },
    {
      path: '/admin/clubs/:clubId(\\d+)',
      name: 'admin-club',
      component: AdminClubsPage,
      props: numberParams('clubId'),
      meta: { requiresAuth: true, requiresAdmin: true, tab: 'profile' },
    },
    {
      path: '/admin/deleted-users',
      name: 'admin-deleted-users',
      component: AdminDeletedUsersPage,
      meta: { requiresAuth: true, requiresAdmin: true, tab: 'profile' },
    },

    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

installGuards(router)
