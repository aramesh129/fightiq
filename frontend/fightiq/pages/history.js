import { useState, useEffect } from 'react'
import Head from 'next/head'
import Link from 'next/link'
import { fetchHistory, initials, formatRecord } from '../lib/api'
import styles from './history.module.css'

export default function History() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [expandedEvent, setExpandedEvent] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetchHistory(page, 100)
      .then(d => {
        setData(prev => page === 1 ? d : [...prev, ...d])
        setHasMore(d.length === 100)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [page])

  // Group bouts by event
  const events = groupByEvent(data)

  return (
    <>
      <Head>
        <title>History — FightIQ</title>
      </Head>

      <div className="page">
        <div className={styles.header}>
          <h1 className={styles.title}>Fight History</h1>
          <p className={styles.subtitle}>Click an event to see all fights, results, and predictions</p>
        </div>

        {loading && page === 1 ? (
          <div className="loading">Loading history</div>
        ) : (
          <div className={styles.eventList}>
            {events.map(ev => {
              const isOpen = expandedEvent === ev.event_id
              const correct = ev.bouts.filter(b => {
                const pred = b.predictions?.[0]
                if (!pred || !b.winner_id) return false
                const predWinner = pred.red_win_probability > 0.5 ? b.fighter_red_id : b.fighter_blue_id
                return predWinner === b.winner_id
              }).length
              const withPred = ev.bouts.filter(b => b.predictions?.[0] && b.winner_id).length

              return (
                <div key={ev.event_id} className={styles.eventBlock}>
                  {/* Event header row — clickable */}
                  <button
                    className={styles.eventRow}
                    onClick={() => setExpandedEvent(isOpen ? null : ev.event_id)}
                  >
                    <div className={styles.eventLeft}>
                      <span className={styles.eventName}>{ev.event_name}</span>
                      <span className={styles.eventDate}>
                        {ev.event_date && new Date(ev.event_date).toLocaleDateString('en-US', {
                          year: 'numeric', month: 'long', day: 'numeric'
                        })}
                      </span>
                    </div>
                    <div className={styles.eventRight}>
                      <span className={styles.boutCount}>{ev.bouts.length} bouts</span>
                      {withPred > 0 && (
                        <span className={styles.accuracy}>
                          {correct}/{withPred} predicted
                        </span>
                      )}
                      <span className={`${styles.chevron} ${isOpen ? styles.chevronOpen : ''}`}>▾</span>
                    </div>
                  </button>

                  {/* Expanded fight rows */}
                  {isOpen && (
                    <div className={styles.boutList}>
                      {ev.bouts.map(bout => {
                        const red = bout.fighter_red
                        const blue = bout.fighter_blue
                        const pred = bout.predictions?.[0]
                        const redProb = pred?.red_win_probability
                        const blueProb = pred?.blue_win_probability
                        const redWon = bout.winner_id === bout.fighter_red_id
                        const blueWon = bout.winner_id === bout.fighter_blue_id
                        const predWinnerId = redProb > 0.5 ? bout.fighter_red_id : bout.fighter_blue_id
                        const predCorrect = pred && bout.winner_id && predWinnerId === bout.winner_id

                        return (
                          <Link key={bout.bout_id} href={`/fight/${bout.bout_id}`} className={styles.boutRow}>
                            {/* Red fighter */}
                            <div className={styles.boutFighter}>
                              <div className={`${styles.boutAvatar} ${styles.boutAvatarRed}`}>
                                {red?.photo_url
                                  ? <img src={red.photo_url} alt="" className={styles.boutAvatarImg} />
                                  : <span>{initials(red?.first_name, red?.last_name)}</span>
                                }
                              </div>
                              <div className={styles.boutFighterInfo}>
                                <span className={`${styles.boutName} ${redWon ? styles.winner : ''}`}>
                                  {red?.first_name} {red?.last_name}
                                  {redWon && <span className={styles.winBadge}>W</span>}
                                </span>
                                <span className={styles.boutRecord}>{formatRecord(red)}</span>
                              </div>
                            </div>

                            {/* Center */}
                            <div className={styles.boutCenter}>
                              {bout.win_method && (
                                <span className={styles.method}>{bout.win_method}</span>
                              )}
                              <span className={styles.boutVs}>vs</span>
                              {pred && (
                                <span className={`${styles.predBadge} ${predCorrect ? styles.predCorrect : predCorrect === false && bout.winner_id ? styles.predWrong : styles.predPending}`}>
                                  {predCorrect === true ? '✓' : predCorrect === false ? '✗' : '?'}
                                </span>
                              )}
                            </div>

                            {/* Blue fighter */}
                            <div className={`${styles.boutFighter} ${styles.boutFighterRight}`}>
                              <div className={styles.boutFighterInfo} style={{ textAlign: 'right' }}>
                                <span className={`${styles.boutName} ${blueWon ? styles.winner : ''}`}>
                                  {blueWon && <span className={styles.winBadge}>W</span>}
                                  {blue?.first_name} {blue?.last_name}
                                </span>
                                <span className={styles.boutRecord}>{formatRecord(blue)}</span>
                              </div>
                              <div className={`${styles.boutAvatar} ${styles.boutAvatarBlue}`}>
                                {blue?.photo_url
                                  ? <img src={blue.photo_url} alt="" className={styles.boutAvatarImg} />
                                  : <span>{initials(blue?.first_name, blue?.last_name)}</span>
                                }
                              </div>
                            </div>

                            {/* Prediction probabilities */}
                            {pred && (
                              <div className={styles.boutProbs}>
                                <span className={styles.redProb}>{Math.round(redProb * 100)}%</span>
                                <div className={styles.boutBar}>
                                  <div className={styles.boutBarFill} style={{ '--pct': `${Math.round(redProb * 100)}%` }} />
                                </div>
                                <span className={styles.blueProb}>{Math.round(blueProb * 100)}%</span>
                              </div>
                            )}
                          </Link>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}

            {hasMore && !loading && (
              <button className={styles.loadMore} onClick={() => setPage(p => p + 1)}>
                Load More
              </button>
            )}
            {loading && page > 1 && <div className="loading">Loading</div>}
          </div>
        )}
      </div>
    </>
  )
}

function groupByEvent(bouts) {
  const map = {}
  for (const b of bouts) {
    const ev = b.events || {}
    const eid = b.event_id || ev.event_id
    if (!eid) continue
    if (!map[eid]) {
      map[eid] = {
        event_id: eid,
        event_name: ev.name || 'Unknown Event',
        event_date: ev.event_date,
        bouts: [],
      }
    }
    map[eid].bouts.push(b)
  }
  return Object.values(map).sort((a, b) => new Date(b.event_date) - new Date(a.event_date))
}
