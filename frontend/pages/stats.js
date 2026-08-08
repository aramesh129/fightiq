import { useState, useEffect } from 'react'
import Head from 'next/head'
import { fetchModelStats } from '../lib/api'
import styles from './stats.module.css'

export default function Stats() {
  const [versions, setVersions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchModelStats()
      .then(setVersions)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const latest = versions[0]

  return (
    <>
      <Head>
        <title>Model Stats — FightIQ</title>
      </Head>

      <div className="page">
        <div className={styles.header}>
          <h1 className={styles.title}>Model Stats</h1>
          <p className={styles.subtitle}>Performance metrics for the FightIQ prediction model</p>
        </div>

        {loading ? (
          <div className="loading">Loading stats</div>
        ) : !latest ? (
          <div className={styles.empty}>No model versions found</div>
        ) : (
          <>
            {/* Hero metrics */}
            <div className={styles.metricsGrid}>
              <div className={styles.metricCard}>
                <div className={styles.metricVal} style={{ color: '#e3000f' }}>
                  {latest.accuracy ? `${(latest.accuracy * 100).toFixed(1)}%` : '—'}
                </div>
                <div className={styles.metricLabel}>Accuracy</div>
                <div className={styles.metricSub}>Test set</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricVal}>
                  {latest.roc_auc ? latest.roc_auc.toFixed(3) : '—'}
                </div>
                <div className={styles.metricLabel}>ROC AUC</div>
                <div className={styles.metricSub}>Discrimination</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricVal}>
                  {latest.brier_score ? latest.brier_score.toFixed(3) : '—'}
                </div>
                <div className={styles.metricLabel}>Brier Score</div>
                <div className={styles.metricSub}>Lower is better</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricVal}>
                  {latest.log_loss ? latest.log_loss.toFixed(3) : '—'}
                </div>
                <div className={styles.metricLabel}>Log Loss</div>
                <div className={styles.metricSub}>Calibration</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricVal}>
                  {latest.train_size?.toLocaleString() || '—'}
                </div>
                <div className={styles.metricLabel}>Training Fights</div>
                <div className={styles.metricSub}>{latest.test_size?.toLocaleString()} test</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricVal} style={{ fontSize: '20px' }}>
                  {latest.version || '—'}
                </div>
                <div className={styles.metricLabel}>Current Version</div>
                <div className={styles.metricSub}>
                  {latest.deployed_at ? new Date(latest.deployed_at).toLocaleDateString() : ''}
                </div>
              </div>
            </div>

            {/* Model architecture */}
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>Model Architecture</h2>
              <div className={styles.archCard}>
                <div className={styles.archRow}>
                  <span className={styles.archLabel}>Type</span>
                  <span>Calibrated Voting Ensemble</span>
                </div>
                <div className={styles.archRow}>
                  <span className={styles.archLabel}>Components</span>
                  <span>Random Forest (400 trees) · Gradient Boosting (300) · Logistic Regression</span>
                </div>
                <div className={styles.archRow}>
                  <span className={styles.archLabel}>Weights</span>
                  <span>RF: 2 · GBM: 2 · LR: 1</span>
                </div>
                <div className={styles.archRow}>
                  <span className={styles.archLabel}>Calibration</span>
                  <span>Sigmoid (3-fold CV)</span>
                </div>
                <div className={styles.archRow}>
                  <span className={styles.archLabel}>Features</span>
                  <span>30 (career stats · recent form · physical · trajectory)</span>
                </div>
                <div className={styles.archRow}>
                  <span className={styles.archLabel}>Explainability</span>
                  <span>SHAP TreeExplainer on Random Forest</span>
                </div>
              </div>
            </div>

            {/* Feature groups */}
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>Feature Groups</h2>
              <div className={styles.featureGroups}>
                {[
                  {
                    title: 'Career Differentials',
                    color: '#e3000f',
                    features: ['SLpM diff', 'Strike Accuracy diff', 'SApM diff', 'Strike Defense diff', 'TD Avg diff', 'TD Accuracy diff', 'TD Defense diff', 'Sub Avg diff'],
                  },
                  {
                    title: 'Physical & Record',
                    color: '#ff8c00',
                    features: ['Age diff', 'Reach diff', 'Height diff', 'Red win %', 'Blue win %', 'Win % diff', 'Stance indicators', 'Stance mismatch'],
                  },
                  {
                    title: 'Recent Form (Exp. Weighted)',
                    color: '#4da3ff',
                    features: ['Red recent SLpM', 'Blue recent SLpM', 'Recent SLpM diff', 'Red recent SApM', 'Blue recent SApM', 'Recent SApM diff', 'Red TD defense', 'Blue TD defense'],
                  },
                  {
                    title: 'Trajectory & Meta',
                    color: '#00c850',
                    features: ['Red SApM trend', 'Blue SApM trend', 'Red finish rate', 'Blue finish rate', 'Total fights diff'],
                  },
                ].map(g => (
                  <div key={g.title} className={styles.featureGroup}>
                    <div className={styles.featureGroupTitle} style={{ borderColor: g.color, color: g.color }}>
                      {g.title}
                    </div>
                    <div className={styles.featureList}>
                      {g.features.map(f => (
                        <span key={f} className={styles.featureTag}>{f}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Version history */}
            {versions.length > 1 && (
              <div className={styles.section}>
                <h2 className={styles.sectionTitle}>Version History</h2>
                <div className={styles.versionTable}>
                  <div className={styles.versionHeader}>
                    <span>Version</span>
                    <span>Accuracy</span>
                    <span>AUC</span>
                    <span>Brier</span>
                    <span>Train Size</span>
                    <span>Deployed</span>
                  </div>
                  {versions.map((v, i) => (
                    <div key={v.version || i} className={`${styles.versionRow} ${i === 0 ? styles.versionCurrent : ''}`}>
                      <span>{v.version} {i === 0 && <span className={styles.currentBadge}>current</span>}</span>
                      <span>{v.accuracy ? `${(v.accuracy * 100).toFixed(1)}%` : '—'}</span>
                      <span>{v.roc_auc?.toFixed(3) || '—'}</span>
                      <span>{v.brier_score?.toFixed(3) || '—'}</span>
                      <span>{v.train_size?.toLocaleString() || '—'}</span>
                      <span>{v.deployed_at ? new Date(v.deployed_at).toLocaleDateString() : '—'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}
