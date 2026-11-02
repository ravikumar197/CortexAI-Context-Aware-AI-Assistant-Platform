chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== 'COPILOT_CHAT') {
    return
  }

  // Accept requests only from this extension's own content scripts.
  if (sender.id !== chrome.runtime.id || !sender.tab?.id) {
    sendResponse({ error: 'Unauthorized request.' })
    return
  }

  fetch('http://127.0.0.1:8000/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(message.payload),
  })
    .then(async (response) => {
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'The AI request failed.')
      }

      sendResponse({ data })
    })
    .catch((error) => {
      sendResponse({
        error: error instanceof Error ? error.message : 'Could not reach the local AI backend.',
      })
    })

  return true
})