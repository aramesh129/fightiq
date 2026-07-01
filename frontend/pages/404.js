import Link from 'next/link'
import styles from './404.module.css'

export default function NotFound() {
  return (
    <div className={styles.page}>
      <div className={styles.code}>404</div>
      <div className={styles.message}>Page not found</div>
      <Link href="/" className={styles.back}>← Back to Predictions</Link>
    </div>
  )
}
