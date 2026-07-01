import Link from 'next/link'
import { initials, formatRecord, calcAge } from '../lib/api'
import styles from './FightCard.module.css'

export default function FightCard({ bout, isMain, isCoMain }) {
  const red = bout.fighter_red
  const blue = bout.fighter_blue
  const pred = bout.predictions?.[0] || bout.prediction
  const redProb = pred?.red_win_probability ?? 0.5
  const blueProb = pred?.blue_win_probability ?? 0.5
  const pct = Math.round(redProb * 100)

  return (
    <div className={styles.card}>
      <div className={styles.fighters}>
        {/* Red corner */}
        <div className={styles.corner}>
          <div className={styles.photo} style={{ background: '#1a0000' }}>
            {red?.photo_url
              ? <img src={red.photo_url} alt="" className={styles.img} />
              : <span className={styles.initials}>{initials(red?.first_name, red?.last_name)}</span>
            }
          </div>
          <div className={styles.info}>
            <div className={`${styles.cornerLabel} ${styles.red}`}>Red Corner</div>
            <div className={styles.name}>
              {red?.first_name}<br />{red?.last_name}
            </div>
            <div className={styles.record}>{formatRecord(red)}</div>
            {pred && (
              <div className={`${styles.prob} ${styles.red}`}>{pct}%</div>
            )}
            <div className={styles.meta}>
              {calcAge(red?.birthday) && <span>Age {calcAge(red?.birthday)}</span>}
              {red?.reach_cm && <span>Reach {Math.round(red.reach_cm / 2.54)}"</span>}
            </div>
          </div>
        </div>

        {/* Center */}
        <div className={styles.center}>
          <div className={styles.vs}>VS</div>
          {bout.weight_class && (
            <div className={styles.weightClass}>{bout.weight_class}</div>
          )}
          {bout.rounds && (
            <div className={styles.rounds}>{bout.rounds} Rounds</div>
          )}
          {pred && (
            <div className={styles.bar}>
              <div className={styles.barFill} style={{ '--pct': `${pct}%` }} />
            </div>
          )}
        </div>

        {/* Blue corner */}
        <div className={`${styles.corner} ${styles.cornerBlue}`}>
          <div className={`${styles.photo} ${styles.photoBlue}`} style={{ background: '#00001a' }}>
            {blue?.photo_url
              ? <img src={blue.photo_url} alt="" className={styles.img} />
              : <span className={styles.initials}>{initials(blue?.first_name, blue?.last_name)}</span>
            }
          </div>
          <div className={`${styles.info} ${styles.infoRight}`}>
            <div className={`${styles.cornerLabel} ${styles.blueLabel}`}>Blue Corner</div>
            <div className={styles.name}>
              {blue?.first_name}<br />{blue?.last_name}
            </div>
            <div className={styles.record}>{formatRecord(blue)}</div>
            {pred && (
              <div className={`${styles.prob} ${styles.blue}`}>{Math.round(blueProb * 100)}%</div>
            )}
            <div className={`${styles.meta} ${styles.metaRight}`}>
              {calcAge(blue?.birthday) && <span>Age {calcAge(blue?.birthday)}</span>}
              {blue?.reach_cm && <span>Reach {Math.round(blue.reach_cm / 2.54)}"</span>}
            </div>
          </div>
        </div>
      </div>

      {/* Footer bar */}
      <div className={styles.footer}>
        <div className={styles.footerLeft}>
          {isMain && <span className={styles.badge}>Main Event</span>}
          {isCoMain && <span className={styles.badgeGray}>Co-Main</span>}
          {pred && (
            <span className={styles.footerProb}>
              {red?.last_name} {pct}% &nbsp;·&nbsp; {blue?.last_name} {Math.round(blueProb * 100)}%
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
