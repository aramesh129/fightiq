import { useRouter } from 'next/router'
import Link from 'next/link'
import styles from './Navbar.module.css'

export default function Navbar() {
  const router = useRouter()
  const path = router.pathname

  return (
    <nav className={styles.nav}>
      <div className={styles.inner}>
        <Link href="/" className={styles.logo}>
          <div className={styles.logoIcon}>F</div>
          <span className={styles.logoText}>FIGHTIQ</span>
        </Link>
        <div className={styles.links}>
          <Link href="/" className={`${styles.link} ${path === '/' ? styles.active : ''}`}>
            Predictions
          </Link>
          <Link href="/history" className={`${styles.link} ${path === '/history' ? styles.active : ''}`}>
            History
          </Link>
          <Link href="/stats" className={`${styles.link} ${path === '/stats' ? styles.active : ''}`}>
            Model Stats
          </Link>
        </div>
      </div>
    </nav>
  )
}
