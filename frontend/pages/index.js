import { useState, useEffect } from 'react'
import Head from 'next/head'
import FightCard from '../components/FightCard'
import { fetchUpcoming } from '../lib/api'
import styles from './index.module.css'

export default function Home() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedEvent, setSelectedEvent] = useState(null)

  useEffect(() => {
    fetchUpcoming()
      .then(d => {
        setData(d)
        const events = groupByEvent(d)
        if (events.length > 0) setSelectedEvent(events[0].event_id)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const events = groupByEvent(data)
  const currentEvent = events.find(e => e.event_id === selectedEvent)
  const bouts = [...(currentEvent?.bouts || [])].sort((a, b) => b.bout_order - a.bout_order)

  function daysUntil(dateStr) {
    if (!dateStr) return null
    return Math.max(0, Math.ceil((new Date(dateStr) - new Date()) / (1000 * 60 * 60 * 24)))
  }

  return (
    <>
      <Head><title>FightIQ — UFC Fight Predictions</title></Head>
      <div className="page">
        {loading ? (
          <div className="loading">Loading predictions</div>
        ) : events.length === 0 ? (
          <div className={styles.empty}>No upcoming events found</div>
        ) : (
          <>
            <div className={styles.eventTabs}>
              {events.map(ev => (
                <button
                  key={ev.event_id}
                  onClick={() => setSelectedEvent(ev.event_id)}
                  className={`${styles.tab} ${selectedEvent === ev.event_id ? styles.tabActive : ''}`}
                >
                  {ev.event_name}
                  <span className={styles.tabDate}>
                    {ev.event_date ? new Date(ev.event_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : ''}
                  </span>
                </button>
              ))}
            </div>

            {currentEvent && (
              <div className={styles.eventHeader}>
                <div>
                  <div className={styles.eventLabel}>Upcoming Event</div>
                  <h1 className={styles.eventName}>{currentEvent.event_name}</h1>
                  <div className={styles.eventMeta}>
                    {currentEvent.event_date && new Date(currentEvent.event_date).toLocaleDateString('en-US', {
                      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                    })}
                  </div>
                </div>
                <div className={styles.countdown}>
                  <div className={styles.countdownLabel}>Days Until Event</div>
                  <div className={styles.countdownNum}>{daysUntil(currentEvent.event_date)}</div>
                </div>
              </div>
            )}

            <div className={styles.fights}>
              {bouts.map((bout, i) => (
                <FightCard key={bout.bout_id} bout={bout} isMain={i === 0} isCoMain={i === 1} />
              ))}
            </div>
          </>
        )}
      </div>
    </>
  )
}

function groupByEvent(data) {
  const map = {}
  for (const row of data) {
    const eid = row.event_id
    if (!map[eid]) {
      map[eid] = {
        event_id: eid,
        event_name: row.event_name || 'Unknown Event',
        event_date: row.event_date,
        bouts: [],
      }
    }
    map[eid].bouts.push(row)
  }
  return Object.values(map).sort((a, b) => new Date(a.event_date) - new Date(b.event_date))
}