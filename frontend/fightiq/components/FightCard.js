import Link from 'next/link'
import { initials } from '../lib/api'
import styles from './FightCard.module.css'

export default function FightCard({ bout, isMain, isCoMain }) {
  // Upcoming API is flat
  const redName = bout.red_fighter || ''
  const blueName = bout.blue_fighter || ''
  const redPhoto = bout.red_photo_url
  const bluePhoto = bout.blue_photo_url
  const redRecord = bout.red_record || ''
  const blueRecord = bout.blue_record || ''
  const redProb = bout.red_win_probability ?? null
  const blueProb = bout.blue_win_probability ?? null
  const hasPred = redProb !== null
  const pct = hasPred ? Math.round(redProb * 100) : 50

  return (
    <div className={styles.card}>
      <div className={styles.fighters}>
        {/* Red corner */}
        <div className={styles.corner}>
          <div className={styles.photo}>
            {redPhoto
              ? <img src={redPhoto} alt={redName} className={styles.img} onError={e => { e.target.style.display='none'; e.target.nextSibling.style.display='flex' }} />
              : null}
            <span className={styles.initials} style={{ display: redPhoto ? 'none' : 'flex' }}>{initials(redName)}</span>
          </div>
          <div className={styles.info}>
            <div className={`${styles.cornerLabel} ${styles.red}`}>Red Corner</div>
            <div className={styles.name}>{redName}</div>
            <div className={styles.record}>{redRecord}</div>
            {hasPred && <div className={`${styles.prob} ${styles.red}`}>{pct}%</div>}
          </div>
        </div>

        {/* Center */}
        <div className={styles.center}>
          <div className={styles.vs}>VS</div>
          {bout.weight_class && <div className={styles.weightClass}>{bout.weight_class}</div>}
          {bout.rounds && <div className={styles.rounds}>{bout.rounds} Rounds</div>}
          {hasPred && (
            <div className={styles.bar}>
              <div className={styles.barFill} style={{ '--pct': `${pct}%` }} />
            </div>
          )}
        </div>

        {/* Blue corner */}
        <div className={`${styles.corner} ${styles.cornerBlue}`}>
          <div className={`${styles.info} ${styles.infoRight}`}>
            <div className={`${styles.cornerLabel} ${styles.blueLabel}`}>Blue Corner</div>
            <div className={styles.name}>{blueName}</div>
            <div className={styles.record}>{blueRecord}</div>
            {hasPred && <div className={`${styles.prob} ${styles.blue}`}>{Math.round(blueProb * 100)}%</div>}
          </div>
          <div className={`${styles.photo} ${styles.photoBlue}`}>
            {bluePhoto
              ? <img src={bluePhoto} alt={blueName} className={styles.img} onError={e => { e.target.style.display='none'; e.target.nextSibling.style.display='flex' }} />
              : null}
            <span className={styles.initials} style={{ display: bluePhoto ? 'none' : 'flex' }}>{initials(blueName)}</span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className={styles.footer}>
        <div className={styles.footerLeft}>
          {isMain && <span className={styles.badge}>Main Event</span>}
          {isCoMain && <span className={styles.badgeGray}>Co-Main</span>}
          {hasPred && (
            <span className={styles.footerProb}>
              {redName.split(' ').pop()} {pct}% · {blueName.split(' ').pop()} {Math.round(blueProb * 100)}%
            </span>
          )}
        </div>
        <Link href={`/fight/${bout.bout_id}`} className={styles.viewLink}>
          Full Analysis →
        </Link>
      </div>
    </div>
  )
}
