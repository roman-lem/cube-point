import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'
import { fetchHomeClubId, useCurrentClubStore } from '@/entities/club'
import { useUserStore } from '@/entities/user'
import { AdminClubCreatePage } from '@/pages/admin-club-create'
import { AdminClubsPage } from '@/pages/admin-clubs'
import { AdminDeletedUsersPage } from '@/pages/admin-deleted-users'
import { AdminUsersPage } from '@/pages/admin-users'
import { AuthPage } from '@/pages/auth'
import { ChangePasswordPage } from '@/pages/change-password'
import { ClubPage } from '@/pages/club'
import { ClubRecordsPage } from '@/pages/club-records'
import { ClubsPage } from '@/pages/clubs'
import { ClubMembersPage } from '@/pages/club-members'
import { ClubSettingsPage } from '@/pages/club-settings'
import { ConsentPage } from '@/pages/consent'
import { EmailConfirmPage } from '@/pages/email-confirm'
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
    /** Logged-in users only: a guest is sent to login. */
    requiresAuth?: boolean
    /** Administrator only: others are sent to the home page. */
    requiresAdmin?: boolean
    /** Guests only: a logged-in user is sent further (login, registration). */
    guestOnly?: boolean
    /** Page without navigation (printing). */
    bare?: boolean
    /** Landing layout: its own header instead of the app tabs. */
    layout?: 'landing'
    /** Which navigation tab is highlighted. */
    tab?: 'club' | 'timer' | 'records' | 'statistics' | 'profile' | 'members'
  }
}

/** Numeric route params as page props: /clubs/5 → { clubId: 5 }. */
const numberParams = (...names: string[]) => (route: RouteLocationNormalized) =>
  Object.fromEntries(names.map((name) => [name, Number(route.params[name])]))

// Pages without requiresAuth are open to everyone, including guests.
export const router = createRouter({
  history: createWebHistory(),
  // Links to page sections (/privacy#processing) scroll to them.
  scrollBehavior(to, _from, savedPosition) {
    if (to.hash) {
      return { el: to.hash }
    }
    return savedPosition ?? false
  },
  routes: [
    // Site root: a logged-in user with a club goes to the last club they opened
    // (or the club of their latest meetup), guests and users without a club get the landing.
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
          const clubId = await fetchHomeClubId(useCurrentClubStore().rememberedId)
          return clubId ? { name: 'club', params: { clubId } } : true
        } catch {
          return true
        }
      },
    },
    // All clubs: open to everyone, a logged-in user is not redirected anywhere.
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
    // The link from the email confirmation letter: open without logging in.
    { path: '/confirm-email', name: 'email-confirm', component: EmailConfirmPage },

    // Club
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

    // Meetups
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

    // Public member profile. One's own highlights the "Profile" tab (see AppNavigation).
    {
      path: '/users/:userId(\\d+)',
      name: 'user-profile',
      component: UserProfilePage,
      props: numberParams('userId'),
      meta: { tab: 'members' },
    },

    // Tabs of a logged-in user
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
    // The "Profile" tab is one's own public profile (requiresAuth: the user is already loaded).
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

    // Administration (an item in the "Profile" tab)
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
      path: '/admin/users',
      name: 'admin-users',
      component: AdminUsersPage,
      meta: { requiresAuth: true, requiresAdmin: true, tab: 'profile' },
    },
    {
      path: '/admin/users/:userId(\\d+)',
      name: 'admin-user',
      component: AdminUsersPage,
      props: numberParams('userId'),
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
