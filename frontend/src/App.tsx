
import { useEffect, useState } from 'react'
import './App.css'

type ChromeTab = {
  id?: number
  url?: string
}

function App() {
  const [enabled, setEnabled] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // useEffect(() => {
  //   chrome.storage.local.get('copilotEnabled', (result) => {
  //     setEnabled(result.copilotEnabled === true)
  //     setLoading(false)
  //   })
  // }, [])


  useEffect(() => {
    let cancelled = false

    async function restoreCopilot() {
      try {
        const stored = await chrome.storage.local.get('copilotEnabled')

        if (cancelled) return

        const isEnabled = stored.copilotEnabled === true
        setEnabled(isEnabled)

        if (!isEnabled) return

        const [tab] = await chrome.tabs.query({
          active: true,
          currentWindow: true,
        })

        if (
          !tab?.id ||
          !tab.url ||
          !/^https?:\/\//i.test(tab.url)
        ) {
          return
        }

        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ['overlay.js'],
        })
      } catch (err) {
        console.error('Could not restore Copilot:', err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void restoreCopilot()

    return () => {
      cancelled = true
    }
  }, [])


  async function getActiveTab(): Promise<ChromeTab> {
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    })

    if (!tab?.id || !tab.url || !/^https?:\/\//i.test(tab.url)) {
      throw new Error(
        'Open a normal website (http or https) before enabling Copilot.',
      )
    }

    return { id: tab.id, url: tab.url }
  }

  async function enableCopilot() {
    setError('')
    setLoading(true)

    try {
      const tab = await getActiveTab()

      await chrome.scripting.executeScript({
        target: { tabId: tab.id! },
        files: ['overlay.js'],
      })

      await chrome.storage.local.set({ copilotEnabled: true })
      setEnabled(true)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not enable Copilot on this page.',
      )
    } finally {
      setLoading(false)
    }
  }

  async function disableCopilot() {
    setError('')
    setLoading(true)

    try {
      const tab = await getActiveTab()

      await chrome.scripting.executeScript({
        target: { tabId: tab.id! },
        func: () => {
          document.getElementById('live-ai-copilot-overlay')?.remove()
        },
      })

      await chrome.storage.local.set({ copilotEnabled: false })
      setEnabled(false)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not disable Copilot on this page.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="copilot">
      <header className="header">
        <div className="logo">✦</div>
        <div>
          <h1>Live AI Copilot</h1>
          <p>Private, local AI assistance</p>
        </div>
      </header>

      <section className="intro">
        <span className="status-dot" />
        <span>{enabled ? 'Copilot is enabled' : 'Copilot is disabled'}</span>
      </section>

      <p className="enable-description">
        {enabled
          ? 'The floating copilot panel has been enabled for the page where you turned it on.'
          : 'Enable Copilot to see contextual suggestions in the bottom-right corner of a webpage.'}
      </p>

      <button
        className="primary-button"
        disabled={loading}
        onClick={() => void (enabled ? disableCopilot() : enableCopilot())}
      >
        {loading ? 'Please wait…' : enabled ? 'Disable Copilot' : 'Enable Copilot'}
      </button>

      {error && <div className="error">{error}</div>}

      <footer>Runs locally on your Mac · Ollama</footer>
    </main>
  )
}

export default App
