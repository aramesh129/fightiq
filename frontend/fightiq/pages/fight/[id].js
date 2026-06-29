import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import Link from 'next/link'
import { fetchFight, initials, formatRecord, calcAge } from '../../lib/api'
import styles from './[id].module.css'

export default function FightDetail() {
  const router = useRouter()
  const { id } = router.query
  const [bout, setBout] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    fetchFight(id)
      .then(setBout)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="page"><div className="loading">Loading fight</div></div>
  if (!bout) return <div className="page"><div className="loading">Fight not found</div></div>

  const red = bout.fighter_red
  const blue = bout.fighter_blue
  const pred = bout.predictions?.[0]
  const redProb = pred?.red_win_probability ?? 0.5
  const blueProb = pred?.blue_win_probability ?? 0.5
  const pct = Math.round(redProb * 100)
  const redWon = bout.winner_id === bout.fighter_red_id
  const blueWon = bout.winner_id === bout.fighter_blue_id
  const isComplete = !!bout.winner_id

  // Find fighter stats
  const redStats = bout.fight_stats?.find(s => s.fighter_id === bout.fighter_red_id)
  const blueStats = bout.fight_stats?.find(s => s.fighter_id === bout.fighter_blue_id)

  // Top SHAP features
  const shapValues = pred?.shap_values || {}
  const topFeatures = Object.entries(shapValues)
    .map(([k, v]) => ({ key: k, val: v, abs: Math.abs(v) }))
    .sort((a, b) => b.abs - a.abs)
    .slice(0, 8)

  return (
    <>
      <Head>
        <title>{red?.last_name} vs {blue?.last_name} — FightIQ</title>
      </Head>
      <div className="page">
        {/* Breadcrumb */}
        <div className={styles.breadcrumb}>
          <Link href="/">Predictions</Link>
          <span>›</span>
          <span>{bout.events?.name}</span>
        </div>

        {/* Hero */}
        <div className={styles.hero}>
          {/* Red side */}
          <div className={`${styles.heroSide} ${styles.heroRed} ${redWon ? styles.heroWinner : ''}`}>
            <div className={styles.heroPhoto}>
              {red?.photo_url
                ? <img src={red.photo_url} alt="" className={styles.heroImg} />
                : <span className={styles.heroInitials}>{initials(red?.first_name, red?.last_name)}</span>
              }
            </div>
            <div className={styles.heroInfo}>
              <div className={`${styles.cornerTag} ${styles.cornerTagRed}`}>
                {isComplete && redWon ? 'Winner · Red Corner' : 'Red Corner'}
              </div>
              <h1 className={styles.heroName}>{red?.first_name} {red?.last_name}</h1>
              {pred && <div className={`${styles.heroProb} ${styles.heroProb}`} style={{ color: '#e3000f' }}>{pct}%</div>}
              <div className={styles.heroProbLabel}>Win Probability</div>
              <div className={styles.heroStats}>
                <div className={styles.heroStat}>
                  <span>{formatRecord(red)}</span>
                  <span className={styles.heroStatLabel}>Record</span>
                </div>
                <div className={styles.heroStat}>
                  <span>{red?.slpm?.toFixed(1) || '—'}</span>
                  <span className={styles.heroStatLabel}>SLpM</span>
                </div>
                <div className={styles.heroStat}>
                  <span>{red?.td_def ? `${Math.round(red.td_def * 100)}%` : '—'}</span>
                  <span className={styles.heroStatLabel}>TD Def</span>
                </div>
                <div className={styles.heroStat}>
                  <span>{calcAge(red?.birthday) || '—'}</span>
                  <span className={styles.heroStatLabel}>Age</span>
                </div>
                <div className={styles.heroStat}>
                  <span>{red?.reach_cm ? `${Math.round(red.reach_cm / 2.54)}"` : '—'}</span>
                  <span className={styles.heroStatLabel}>Reach</span>
                </div>
              </div>
            </div>
          </div>

          {/* Center */}
          <div className={styles.heroCenter}>
            <div className={styles.heroVs}>VS</div>
            {pred && (
              <>
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
                <div className={styles.probBar}>
                  <div className={styles.probBarFill} style={{ '--pct': `${pct}%` }} />
                </div>
              </>
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
            <div className={`${styles.heroPhoto} ${styles.heroPhotoBlue}`}>
              {blue?.photo_url
                ? <img src={blue.photo_url} alt="" className={styles.heroImg} />
                : <span className={styles.heroInitials}>{initials(blue?.first_name, blue?.last_name)}</span>
              }
            </div>
            <div className={`${styles.heroInfo} ${styles.heroInfoRight}`}>
              <div className={`${styles.cornerTag} ${styles.cornerTagBlue}`}>
                {isComplete && blueWon ? 'Winner · Blue Corner' : 'Blue Corner'}
              </div>
              <h1 className={styles.heroName}>{blue?.first_name} {blue?.last_name}</h1>
              {pred && <div className={styles.heroProb} style={{ color: '#4da3ff' }}>{Math.round(blueProb * 100)}%</div>}
              <div className={styles.heroProbLabel}>Win Probability</div>
              <div className={`${styles.heroStats} ${styles.heroStatsRight}`}>
                <div className={styles.heroStat}>
                  <span>{formatRecord(blue)}</span>
                  <span className={styles.heroStatLabel}>Record</span>
                </div>
                <div className={styles.heroStat}>
                  <span>{blue?.slpm?.toFixed(1) || '—'}</span>
                  <span className={styles.heroStatLabel}>SLpM</span>
                </div>
                <div className={styles.heroStat}>
                  <span>{blue?.td_def ? `${Math.round(blue.td_def * 100)}%` : '—'}</span>
                  <span className={styles.heroStatLabel}>TD Def</span>
                </div>
                <div className={styles.heroStat}>
                  <span>{calcAge(blue?.birthday) || '—'}</span>
                  <span className={styles.heroStatLabel}>Age</span>
                </div>
                <div className={styles.heroStat}>
                  <span>{blue?.reach_cm ? `${Math.round(blue.reach_cm / 2.54)}"` : '—'}</span>
                  <span className={styles.heroStatLabel}>Reach</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Fight stats table */}
        {(redStats || blueStats) && (
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Fight Stats</h2>
            <div className={styles.statsTable}>
              {[
                ['Sig. Strikes Landed', redStats?.sig_str_landed, blueStats?.sig_str_landed],
                ['Sig. Strikes Attempted', redStats?.sig_str_attempted, blueStats?.sig_str_attempted],
                ['Total Strikes', redStats?.total_str_landed, blueStats?.total_str_landed],
                ['Takedowns Landed', redStats?.td_landed, blueStats?.td_landed],
                ['Takedowns Attempted', redStats?.td_attempted, blueStats?.td_attempted],
                ['Knockdowns', redStats?.knockdowns, blueStats?.knockdowns],
                ['Submission Attempts', redStats?.sub_attempts, blueStats?.sub_attempts],
              ].map(([label, rv, bv]) => {
                if (rv == null && bv == null) return null
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

        {/* SHAP features */}
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
                      <div
                        className={styles.shapBar}
                        style={{
                          width,
                          background: favorsRed ? '#e3000f' : '#1a6fc4',
                          marginLeft: favorsRed ? 'auto' : '0',
                        }}
                      />
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
