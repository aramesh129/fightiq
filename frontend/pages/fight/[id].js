import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import Link from 'next/link'
import { fetchFight, initialsFromParts, initials, calcAge } from '../../lib/api'
import styles from './[id].module.css'

export default function FightDetail() {
  const router = useRouter()
  const { id } = router.query
  const [bout, setBout] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    fetchFight(id).then(setBout).catch(console.error).finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="page"><div className="loading">Loading fight</div></div>
  if (!bout) return <div className="page"><div className="loading">Fight not found</div></div>

  // Support both flat (upcoming) and nested (history) structures
  const isFlat = !!bout.red_fighter
  const redName = isFlat ? bout.red_fighter : `${bout.fighter_red?.first_name || ''} ${bout.fighter_red?.last_name || ''}`.trim()
  const blueName = isFlat ? bout.blue_fighter : `${bout.fighter_blue?.first_name || ''} ${bout.fighter_blue?.last_name || ''}`.trim()
  const redPhoto = isFlat ? bout.red_photo_url : bout.fighter_red?.photo_url
  const bluePhoto = isFlat ? bout.blue_photo_url : bout.fighter_blue?.photo_url
  const redRecord = isFlat ? bout.red_record : null
  const blueRecord = isFlat ? bout.blue_record : null

  const pred = isFlat ? bout : bout.predictions
  const redProb = pred?.red_win_probability ?? null
  const blueProb = pred?.blue_win_probability ?? null
  const hasPred = redProb !== null
  const pct = hasPred ? Math.round(redProb * 100) : 50

  const redWon = bout.winner_id && bout.winner_id === bout.fighter_red_id
  const blueWon = bout.winner_id && bout.winner_id === bout.fighter_blue_id
  const isComplete = !!bout.winner_id
  const eventName = isFlat ? bout.event_name : (bout.events?.event_name || bout.events?.name)

  const redStats = bout.fight_stats?.find(s => s.fighter_id === bout.fighter_red_id)
  const blueStats = bout.fight_stats?.find(s => s.fighter_id === bout.fighter_blue_id)

  const shapValues = pred?.shap_values || {}
  const topFeatures = Object.entries(shapValues)
    .map(([k, v]) => ({ key: k, val: v, abs: Math.abs(v) }))
    .sort((a, b) => b.abs - a.abs)
    .slice(0, 8)

  return (
    <>
      <Head><title>{redName} vs {blueName} — FightIQ</title></Head>
      <div className="page">
        <div className={styles.breadcrumb}>
          <Link href="/">Predictions</Link>
          <span>›</span>
          <span>{eventName}</span>
        </div>

        <div className={styles.hero}>
          {/* Red side */}
          <div className={`${styles.heroSide} ${styles.heroRed} ${redWon ? styles.heroWinner : ''}`}>
            <div className={styles.heroPhoto}>
              {redPhoto
                ? <img src={redPhoto} alt={redName} className={styles.heroImg} onError={e => e.target.style.display='none'} />
                : null}
              <span className={styles.heroInitials}>{initials(redName)}</span>
            </div>
            <div className={styles.heroInfo}>
              <div className={`${styles.cornerTag} ${styles.cornerTagRed}`}>
                {isComplete && redWon ? 'Winner · Red Corner' : 'Red Corner'}
              </div>
              <h1 className={styles.heroName}>{redName}</h1>
              {redRecord && <div className={styles.heroRecord}>{redRecord}</div>}
              {hasPred && <div className={styles.heroProb} style={{ color: '#e3000f' }}>{pct}%</div>}
              <div className={styles.heroProbLabel}>Win Probability</div>
            </div>
          </div>

          {/* Center */}
          <div className={styles.heroCenter}>
            <div className={styles.heroVs}>VS</div>
            {bout.weight_class && <div className={styles.heroWeightClass}>{bout.weight_class}</div>}
            {hasPred && (
              <div className={styles.monteCarlo}>
                <div className={styles.monteCarloTitle}>Monte Carlo Results</div>
                <div className={styles.monteCarloRow}>
                  <span>Decision</span>
                  <span>{Math.round((pred.decision_probability || 0) * 100)}%</span>
                </div>
                <div className={styles.monteCarloRow}>
                  <span>KO / TKO</span>
                  <span>{Math.round((pred.ko_probability || 0) * 100)}%</span>
                </div>
                <div className={styles.monteCarloRow}>
                  <span>Submission</span>
                  <span>{Math.round((pred.submission_probability || 0) * 100)}%</span>
                </div>
              </div>
            )}
            {hasPred && (
              <div className={styles.probBar}>
                <div className={styles.probBarFill} style={{ '--pct': `${pct}%` }} />
              </div>
            )}
            {isComplete && bout.win_method && (
              <div className={styles.result}>
                <div className={styles.resultLabel}>Result</div>
                <div className={styles.resultMethod}>{bout.win_method}</div>
              </div>
            )}
          </div>

          {/* Blue side */}
          <div className={`${styles.heroSide} ${styles.heroBlue} ${blueWon ? styles.heroWinner : ''}`}>
            <div className={`${styles.heroInfo} ${styles.heroInfoRight}`}>
              <div className={`${styles.cornerTag} ${styles.cornerTagBlue}`}>
                {isComplete && blueWon ? 'Winner · Blue Corner' : 'Blue Corner'}
              </div>
              <h1 className={styles.heroName}>{blueName}</h1>
              {blueRecord && <div className={styles.heroRecord}>{blueRecord}</div>}
              {hasPred && <div className={styles.heroProb} style={{ color: '#4da3ff' }}>{Math.round(blueProb * 100)}%</div>}
              <div className={styles.heroProbLabel}>Win Probability</div>
            </div>
            <div className={`${styles.heroPhoto} ${styles.heroPhotoBlue}`}>
              {bluePhoto
                ? <img src={bluePhoto} alt={blueName} className={styles.heroImg} onError={e => e.target.style.display='none'} />
                : null}
              <span className={styles.heroInitials}>{initials(blueName)}</span>
            </div>
          </div>
        </div>

        {/* Fight stats */}
        {(redStats || blueStats) && (
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Fight Stats</h2>
            <div className={styles.statsTable}>
              {[
                ['Sig. Strikes', redStats?.sig_str_landed, blueStats?.sig_str_landed],
                ['Total Strikes', redStats?.total_str_landed, blueStats?.total_str_landed],
                ['Takedowns', redStats?.td_landed, blueStats?.td_landed],
                ['Knockdowns', redStats?.knockdowns, blueStats?.knockdowns],
                ['Sub Attempts', redStats?.sub_attempts, blueStats?.sub_attempts],
              ].filter(([, rv, bv]) => rv != null || bv != null).map(([label, rv, bv]) => {
                const total = (rv || 0) + (bv || 0)
                const redPct = total > 0 ? (rv || 0) / total : 0.5
                return (
                  <div key={label} className={styles.statRow}>
                    <span className={styles.statVal} style={{ color: '#e3000f' }}>{rv ?? '—'}</span>
                    <div className={styles.statCenter}>
                      <span className={styles.statLabel}>{label}</span>
                      <div className={styles.statBar}>
                        <div className={styles.statBarFill} style={{ '--pct': `${Math.round(redPct * 100)}%` }} />
                      </div>
                    </div>
                    <span className={styles.statVal} style={{ color: '#4da3ff', textAlign: 'right' }}>{bv ?? '—'}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* SHAP */}
        {topFeatures.length > 0 && (
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Key Prediction Factors</h2>
            <p className={styles.sectionSub}>SHAP values — positive favors red corner, negative favors blue</p>
            <div className={styles.shapList}>
              {topFeatures.map(({ key, val }) => {
                const favorsRed = val > 0
                const maxAbs = topFeatures[0].abs
                const width = `${Math.round((Math.abs(val) / maxAbs) * 100)}%`
                return (
                  <div key={key} className={styles.shapRow}>
                    <span className={styles.shapKey}>{key.replace(/_/g, ' ')}</span>
                    <div className={styles.shapBarWrap}>
                      <div className={styles.shapBar} style={{
                        width,
                        background: favorsRed ? '#e3000f' : '#1a6fc4',
                        marginLeft: favorsRed ? 'auto' : '0'
                      }} />
                    </div>
                    <span className={styles.shapVal} style={{ color: favorsRed ? '#e3000f' : '#4da3ff' }}>
                      {val > 0 ? '+' : ''}{val.toFixed(3)}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </>
  )
}