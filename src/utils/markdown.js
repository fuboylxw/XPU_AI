import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="md-code"><code class="hljs ${lang}">${hljs.highlight(code, { language: lang }).value}</code></pre>`
      } catch (e) { /* ignore */ }
    }
    const safe = md.utils.escapeHtml(code)
    return `<pre class="md-code"><code class="hljs">${safe}</code></pre>`
  }
})

export function renderMarkdown(text) {
  if (!text || typeof text !== 'string') return ''
  return md.render(text)
}

export default md
