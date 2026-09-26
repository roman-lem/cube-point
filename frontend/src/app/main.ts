import { createApp } from 'vue'
import { createPinia } from 'pinia'
// Fonts come from the build, no third-party domains. The browser downloads only
// the subsets (Latin, Cyrillic) used on the page.
import '@fontsource-variable/jetbrains-mono'
import '@fontsource-variable/manrope'
import { SITE_NAME } from '@/shared/config'
import App from './App.vue'
import { setupAuthHandlers } from './providers/auth'
import { router } from './router'
import './styles/global.css'
import './styles/page.css'

document.title = SITE_NAME

const app = createApp(App)
// Pinia is installed before the router: the first navigation already reads the user store.
app.use(createPinia())
setupAuthHandlers(router)
app.use(router)
app.mount('#app')
