import { useState, useEffect } from 'react'
import Head from 'next/head'
import Link from 'next/link'
import { fetchHistory, initialsFromParts } from '../lib/api'
import styles from './history.module.css'

export default function History() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [expandedEvent, setExpandedEvent] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetchHistory(page, 500)
      .then(d => {
        setData(prev => page === 1 ? d : [...prev, ...d])
        setHasMore(d.length === 500)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [page])

  const events = groupByEvent(data)

  return (
    <>
      <Head><title>History — FightIQ</title></Head>
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
              const withPred = ev.bouts.filter(b => b.predictions && b.winner_id).length
              const correct = ev.bouts.filter(b => {
                if (!b.predictions || !b.winner_id) return false
                const predWinner = b.predictions.red_win_probability > 0.5 ? b.fighter_red_id : b.fighter_blue_id
                return predWinner === b.winner_id
              }).length

              return (
                <div key={ev.event_id} className={styles.eventBlock}>
                  <button className={styles.eventRow} onClick={() => setExpandedEvent(isOpen ? null : ev.event_id)}>
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
                        <span className={styles.accuracy}>{correct}/{withPred} predicted correctly</span>
                      )}
                      <span className={`${styles.chevron} ${isOpen ? styles.chevronOpen : ''}`}>▾</span>
                    </div>
                  </button>

                  {isOpen && (
                    <div className={styles.boutList}>
                      {ev.bouts.map(bout => {
                        const red = bout.fighter_red || {}
                        const blue = bout.fighter_blue || {}
                        const redName = `${red.first_name || ''} ${red.last_name || ''}`.trim()
                        const blueName = `${blue.first_name || ''} ${blue.last_name || ''}`.trim()
                        const pred = bout.predictions
                        const redWon = bout.winner_id === bout.fighter_red_id
                        const blueWon = bout.winner_id === bout.fighter_blue_id
                        const predCorrect = pred && bout.winner_id
                          ? (pred.red_win_probability > 0.5 ? bout.fighter_red_id : bout.fighter_blue_id) === bout.winner_id
                          : null

                        return (
                          <Link key={bout.bout_id} href={`/fight/${bout.bout_id}`} className={styles.boutRow}>
                            <div className={styles.boutFighter}>
                              <div className={`${styles.boutAvatar} ${styles.boutAvatarRed}`}>
                                {red.photo_url
                                  ? <img src={red.photo_url} alt="" className={styles.boutAvatarImg} onError={e => e.target.style.display='none'} />
                                  : <span>{initialsFromParts(red.first_name, red.last_name)}</span>}
                              </div>
                              <div className={styles.boutFighterInfo}>
                                <span className={`${styles.boutName} ${redWon ? styles.winner : ''}`}>
                                  {redName}{redWon && <span className={styles.winBadge}>W</span>}
                                </span>
                              </div>
                            </div>

                            <div className={styles.boutCenter}>
                              {bout.win_method && <span className={styles.method}>{bout.win_method}</span>}
                              <span className={styles.boutVs}>vs</span>
                              {predCorrect !== null && (
                                <span className={`${styles.predBadge} ${predCorrect ? styles.predCorrect : styles.predWrong}`}>
                                  {predCorrect ? '✓' : '✗'}
                                </span>
                              )}
                            </div>

                            <div className={`${styles.boutFighter} ${styles.boutFighterRight}`}>
                              <div className={styles.boutFighterInfo} style={{ textAlign: 'right' }}>
                                <span className={`${styles.boutName} ${blueWon ? styles.winner : ''}`}>
                                  {blueWon && <span className={styles.winBadge}>W</span>}{blueName}
                                </span>
                              </div>
                              <div className={`${styles.boutAvatar} ${styles.boutAvatarBlue}`}>
                                {blue.photo_url
                                  ? <img src={blue.photo_url} alt="" className={styles.boutAvatarImg} onError={e => e.target.style.display='none'} />
                                  : <span>{initialsFromParts(blue.first_name, blue.last_name)}</span>}
                              </div>
                            </div>

                            {pred && (
                              <div className={styles.boutProbs}>
                                <span className={styles.redProb}>{Math.round(pred.red_win_probability * 100)}%</span>
                                <div className={styles.boutBar}>
                                  <div className={styles.boutBarFill} style={{ '--pct': `${Math.round(pred.red_win_probability * 100)}%` }} />
                                </div>
                                <span className={styles.blueProb}>{Math.round(pred.blue_win_probability * 100)}%</span>
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
              <button className={styles.loadMore} onClick={() => setPage(p => p + 1)}>Load More</button>
            )}
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
    const eid = b.event_id
    if (!eid) continue
    if (!map[eid]) {
      map[eid] = {
        event_id: eid,
        event_name: ev.event_name || ev.name || 'Unknown Event',
        event_date: ev.event_date,
        bouts: [],
      }
    }
    map[eid].bouts.push(b)
  }
  return Object.values(map).sort((a, b) => new Date(b.event_date) - new Date(a.event_date))
}