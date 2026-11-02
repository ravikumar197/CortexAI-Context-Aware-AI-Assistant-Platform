
export type PageContext = {
  page_title: string
  page_url: string
  page_text: string
}

export function extractPageContext(): PageContext {
  return {
    page_title: document.title || 'Untitled page',
    page_url: window.location.href,
    page_text: (document.body?.innerText ?? '').slice(0, 20000),
  }
}
