import React, { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { copy } from './copy'
import CloudMascot from './CloudMascot'
import EmojiPicker from './EmojiPicker'
import EmojiAutocomplete from './EmojiAutocomplete'
import { searchEmojis } from './emojiData'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Feature flags
const ENABLE_TTS = false // Set to true when TTS backend is ready

// Sticker colors, cycled across the suggestion chips
const CHIP_VARIANTS = ['pink', 'teal', 'lilac']

// Slack-style ":" trigger: colon immediately followed by a word, ending at
// the cursor - ":gato" resolves against the query "gato". No space allowed
// in between, so normal punctuation ("Os animais: cão, gato") never fires it.
const COLON_TRIGGER_RE = /:([a-zA-Z0-9À-ÿ]+)$/

// --- Suggestion pool sampling -----------------------------------------
// The server pool (see api/suggestions/) is topic-tagged: { text, topic }.
// The bundled fallback in copy.js is just plain strings, so it gets a rough
// local topic mapping here (never edited into copy.js itself) purely so the
// same diversity/anti-repeat logic works whether or not the fetch succeeds.
const FALLBACK_TOPICS = [
  'animals', 'weather', 'weather', 'space', 'animals', 'feelings',
  'nature', 'nature', 'fun', 'body', 'tech', 'weather',
]

const normalizeQuestion = (q, idx) => {
  if (typeof q === 'string') {
    return { text: q, topic: FALLBACK_TOPICS[idx % FALLBACK_TOPICS.length] || 'fun' }
  }
  return { text: q.text, topic: q.topic || 'fun' }
}

// Anti-repeat memory: the last ~24 chip texts actually shown, persisted so
// it survives reloads (not just re-renders) - that's the whole point, since
// a kiosk reload is exactly when the old code re-rolled with zero memory.
const RECENT_CHIPS_KEY = 'eli7:recent-chips'
const RECENT_CHIPS_CAP = 24

const getRecentChipTexts = () => {
  try {
    const parsed = JSON.parse(localStorage.getItem(RECENT_CHIPS_KEY) || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

const rememberShownChips = (texts) => {
  try {
    const next = [...getRecentChipTexts(), ...texts].slice(-RECENT_CHIPS_CAP)
    localStorage.setItem(RECENT_CHIPS_KEY, JSON.stringify(next))
  } catch {
    // localStorage unavailable (private mode, quota) - anti-repeat just no-ops
  }
}

const clearRecentChips = () => {
  try {
    localStorage.removeItem(RECENT_CHIPS_KEY)
  } catch {
    // ignore
  }
}

// Picks up to 3 items favoring distinct topics: shuffle the topics present,
// take one random item per topic until we have 3. Tops up from anything
// left over if the candidate set doesn't span 3 topics.
const pickDiverseChips = (candidates) => {
  const byTopic = new Map()
  for (const item of candidates) {
    if (!byTopic.has(item.topic)) byTopic.set(item.topic, [])
    byTopic.get(item.topic).push(item)
  }
  const shuffledTopics = [...byTopic.keys()].sort(() => 0.5 - Math.random())

  const picks = []
  for (const topic of shuffledTopics) {
    if (picks.length >= 3) break
    const items = byTopic.get(topic)
    picks.push(items[Math.floor(Math.random() * items.length)])
  }
  if (picks.length < 3) {
    const pickedTexts = new Set(picks.map(p => p.text))
    for (const item of candidates) {
      if (picks.length >= 3) break
      if (!pickedTexts.has(item.text)) {
        picks.push(item)
        pickedTexts.add(item.text)
      }
    }
  }
  return picks
}

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showChips, setShowChips] = useState(true)
  const [selectedChips, setSelectedChips] = useState([])
  const [idleTimer, setIdleTimer] = useState(null)
  const [conversationHistory, setConversationHistory] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  // { start, end, results, highlighted } for the active ":" match, or null
  const [autocomplete, setAutocomplete] = useState(null)

  const feedRef = useRef(null)
  const inputRef = useRef(null)
  const messagesEndRef = useRef(null)
  const emojiAnchorRef = useRef(null)
  // Suggestion pool to sample chips from - starts on the bundled fallback,
  // swapped for the server pool once /suggestions resolves. Normalized to
  // { text, topic } so sampling below can enforce topic diversity either way.
  const suggestionPoolRef = useRef(copy.starterQuestions.map(normalizeQuestion))

  // Get 3 random starter questions: diverse topics, and avoiding whatever
  // was shown in the last ~24 picks (persisted across reloads). If the pool
  // is exhausted (not enough unseen candidates, or not enough distinct
  // topics left among them) the seen-set resets and we draw from scratch.
  const getRandomChips = useCallback(() => {
    const pool = suggestionPoolRef.current
    if (pool.length === 0) return []

    const recentTexts = new Set(getRecentChipTexts())
    let candidates = pool.filter(item => !recentTexts.has(item.text))

    const poolTopicCount = new Set(pool.map(item => item.topic)).size
    const candidateTopicCount = new Set(candidates.map(item => item.topic)).size
    const exhausted = candidates.length < 3 || candidateTopicCount < Math.min(3, poolTopicCount)
    if (exhausted) {
      clearRecentChips()
      candidates = pool
    }

    const texts = pickDiverseChips(candidates).map(item => item.text)
    rememberShownChips(texts)
    return texts
  }, [])

  // Fetch the self-curating suggestion pool; keep the bundled fallback on any failure
  const loadSuggestionPool = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/suggestions`)
      if (!response.ok) throw new Error('Failed to load suggestions')
      const data = await response.json()
      if (Array.isArray(data.questions) && data.questions.length > 0) {
        suggestionPoolRef.current = data.questions.map(normalizeQuestion)
        setSelectedChips(getRandomChips())
      }
    } catch (err) {
      console.error('Failed to load suggestion pool, using bundled defaults:', err)
    }
  }, [getRandomChips])

  useEffect(() => {
    setSelectedChips(getRandomChips())
    inputRef.current?.focus()
    // Start a new session on mount
    startNewSession()
    loadSuggestionPool()
  }, [getRandomChips, loadSuggestionPool])
  
  // Start a new conversation session
  const startNewSession = async () => {
    try {
      const response = await fetch(`${API_URL}/new-session`, {
        method: 'POST'
      })
      const data = await response.json()
      setSessionId(data.session_id)
    } catch (err) {
      console.error('Failed to start session:', err)
    }
  }
  
  // Auto-resize textarea based on content
  const adjustTextareaHeight = useCallback(() => {
    const textarea = inputRef.current
    if (textarea) {
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = 'auto'
      // Set height to scrollHeight (content height)
      textarea.style.height = `${textarea.scrollHeight}px`
    }
  }, [])

  // Smart focus management
  useEffect(() => {
    // Focus on initial load
    inputRef.current?.focus()
  }, []) // Only on mount
  
  // Focus after window gains focus
  useEffect(() => {
    const handleWindowFocus = () => {
      if (!document.activeElement?.matches('input, textarea, select')) {
        inputRef.current?.focus()
      }
    }
    
    window.addEventListener('focus', handleWindowFocus)
    return () => window.removeEventListener('focus', handleWindowFocus)
  }, [])
  
  // Capture any keyboard input and focus the input
  useEffect(() => {
    const handleKeyPress = (e) => {
      // Don't capture if already typing in an input
      if (document.activeElement?.matches('input, textarea, select')) {
        return
      }
      
      // Don't capture special keys
      if (e.metaKey || e.ctrlKey || e.altKey) {
        return
      }
      
      // If it's a printable character, focus the input
      if (e.key.length === 1 && !e.target.matches('button')) {
        inputRef.current?.focus()
      }
    }
    
    document.addEventListener('keydown', handleKeyPress)
    return () => document.removeEventListener('keydown', handleKeyPress)
  }, [])

  // Scroll to bottom when question is asked
  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      if (feedRef.current) {
        feedRef.current.scrollTop = feedRef.current.scrollHeight
      }
    }, 50)
  }, [])

  // Scroll to show the last question when answer arrives
  const scrollToLastQuestion = useCallback(() => {
    // Use setTimeout to ensure DOM has updated
    setTimeout(() => {
      if (feedRef.current && messages.length > 0) {
        // Find the last bubble group (contains question and answer)
        const bubbleGroups = feedRef.current.querySelectorAll('.bubble-group')
        if (bubbleGroups.length > 0) {
          const lastGroup = bubbleGroups[bubbleGroups.length - 1]
          // Scroll so the question is at the top of the viewport
          // Adding a small offset (80px) to account for any padding
          const topOffset = lastGroup.offsetTop - 80
          feedRef.current.scrollTop = topOffset
        }
      }
    }, 100) // Small delay to ensure answer has rendered
  }, [messages])

  useEffect(() => {
    const lastMessage = messages[messages.length - 1]
    if (lastMessage) {
      if (lastMessage.response) {
        // When answer arrives, scroll to show question at top
        scrollToLastQuestion()
      } else {
        // When question is asked, scroll to bottom to show question + loading
        scrollToBottom()
      }
    }
  }, [messages, scrollToLastQuestion, scrollToBottom])

  // Handle idle state
  useEffect(() => {
    if (idleTimer) clearTimeout(idleTimer)
    
    const timer = setTimeout(() => {
      if (messages.length > 0 && !loading) {
        // Show idle prompt after 20s
        setSelectedChips([copy.idlePrompts[Math.floor(Math.random() * copy.idlePrompts.length)]])
      }
    }, 20000)
    
    setIdleTimer(timer)

    return () => clearTimeout(timer)
  }, [messages, loading])

  // Close the emoji picker when tapping anywhere outside its button/panel
  useEffect(() => {
    if (!showEmojiPicker) return

    const handlePointerDown = (e) => {
      if (emojiAnchorRef.current?.contains(e.target)) return
      setShowEmojiPicker(false)
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [showEmojiPicker])

  // Replaces input[start:end] with `text`, clamps to the 2000-char limit,
  // and restores the caret right after the inserted text once React
  // re-renders - used by both emoji insertion mechanisms.
  const spliceInput = (start, end, text) => {
    const next = (input.slice(0, start) + text + input.slice(end)).slice(0, 2000)
    setInput(next)
    const caretPos = Math.min(start + text.length, next.length)
    requestAnimationFrame(() => {
      const textarea = inputRef.current
      if (!textarea) return
      textarea.focus()
      textarea.setSelectionRange(caretPos, caretPos)
      adjustTextareaHeight()
    })
  }

  // Emoji picker: insert at the current cursor/selection. Panel stays open
  // so several emojis can be tapped in a row.
  const handleEmojiSelect = (char) => {
    const textarea = inputRef.current
    const start = textarea?.selectionStart ?? input.length
    const end = textarea?.selectionEnd ?? input.length
    spliceInput(start, end, char)
  }

  // ":" autocomplete: look for a colon+word token ending at the cursor and
  // find matches; clears itself when the token breaks or nothing matches.
  const updateAutocomplete = (value, caret) => {
    const match = value.slice(0, caret).match(COLON_TRIGGER_RE)
    if (!match) {
      setAutocomplete(null)
      return
    }
    const results = searchEmojis(match[1], 6)
    if (results.length === 0) {
      setAutocomplete(null)
      return
    }
    setAutocomplete({ start: caret - match[0].length, end: caret, results, highlighted: 0 })
    setShowEmojiPicker(false)
  }

  const selectAutocompleteEmoji = (emoji) => {
    if (!autocomplete) return
    spliceInput(autocomplete.start, autocomplete.end, `${emoji.char} `)
    setAutocomplete(null)
  }

  // Handle input submission
  const handleSubmit = async (e, overrideQuestion) => {
    e?.preventDefault()

    const question = (overrideQuestion ?? input).trim()
    if (!question || loading) return
    
    setInput('')
    setLoading(true)
    setError(null)
    setShowChips(false)
    setShowEmojiPicker(false)
    setAutocomplete(null)
    
    // Reset textarea height after submission
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }
    
    // Add question to messages and history
    const newMessageId = Date.now().toString()
    const newMessage = {
      id: newMessageId,
      type: 'question',
      text: question,
      response: null,
      formattedResponse: null
    }
    
    setMessages(prev => [...prev, newMessage])
    
    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question,
          history: conversationHistory,
          session_id: sessionId
        })
      })
      
      if (!response.ok) throw new Error('Failed to get response')
      
      const data = await response.json()
      
      // DEBUG: Log what we received from API
      console.log('=== DEBUG: Frontend received ===')
      console.log('Raw response:', data.response)
      console.log('Response length:', data.response.length)
      console.log('Number of newlines:', (data.response.match(/\n/g) || []).length)
      console.log('================================')
      
      // Update message with answer
      setMessages(prev => prev.map(msg => 
        msg.id === newMessageId
          ? { 
              ...msg, 
              response: data.response
            }
          : msg
      ))
      
      // Update conversation history
      setConversationHistory(prev => [
        ...prev,
        { role: 'user', content: question },
        { role: 'assistant', content: data.response }
      ])
    } catch (err) {
      console.error('Error:', err)
      setError(copy.errors.network)
      // Remove the failed question
      setMessages(prev => prev.filter(msg => msg.id !== newMessageId))
    } finally {
      setLoading(false)
      // Focus input after response is complete
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }


  // Handle chip click
  const handleChipClick = (question) => {
    setInput(question)
    // Trigger textarea resize after setting the input
    setTimeout(() => {
      adjustTextareaHeight()
      handleSubmit(null, question)
      inputRef.current?.focus()
    }, 100)
  }

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (autocomplete) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault()
        const dir = e.key === 'ArrowDown' ? 1 : -1
        setAutocomplete(prev => prev && {
          ...prev,
          highlighted: (prev.highlighted + dir + prev.results.length) % prev.results.length
        })
        return
      }
      if (e.key === 'Enter') {
        e.preventDefault()
        selectAutocompleteEmoji(autocomplete.results[autocomplete.highlighted])
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        setAutocomplete(null)
        return
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    } else if (e.key === 'Escape') {
      setInput('')
    }
  }

  // Retry after error
  const handleRetry = () => {
    setError(null)
    inputRef.current?.focus()
  }
  
  // Start a new topic: clear the visible thread + working history so the
  // next prompt isn't read against it, and let the backend curator distill
  // the finished topic into long-term memory before it's dropped
  const handleReset = () => {
    setMessages([])
    setConversationHistory([])
    setInput('')
    setError(null)
    setShowChips(true)
    setShowEmojiPicker(false)
    setAutocomplete(null)
    setSelectedChips(getRandomChips())
    startNewSession()
    fetch(`${API_URL}/begin-new-topic`, { method: 'POST' }).catch(() => {})
    inputRef.current?.focus()
  }

  return (
    <div className="app" lang="pt">
      <div className="bg-decor" aria-hidden="true">
        <svg className="bg-cloud bg-cloud--pink" width="220" height="150" viewBox="0 0 200 150">
          <g fill="var(--pink-pale)" opacity="0.7">
            <rect x="26" y="70" width="148" height="54" rx="27" />
            <circle cx="54" cy="70" r="34" />
            <circle cx="100" cy="52" r="42" />
            <circle cx="150" cy="72" r="30" />
          </g>
        </svg>
        <svg className="bg-cloud bg-cloud--teal" width="200" height="140" viewBox="0 0 200 150">
          <g fill="var(--teal-pale)" opacity="0.7">
            <rect x="26" y="70" width="148" height="54" rx="27" />
            <circle cx="54" cy="70" r="34" />
            <circle cx="100" cy="52" r="42" />
            <circle cx="150" cy="72" r="30" />
          </g>
        </svg>
        <span className="bg-star bg-star--1">✦</span>
        <span className="bg-star bg-star--2">✦</span>
        <span className="bg-star bg-star--3">✦</span>
      </div>
      {messages.length > 0 && (
        <button className="reset-button" onClick={handleReset} aria-label="Começar de novo">
          <svg className="reset-icon" width="14" height="14" viewBox="0 0 20 20" aria-hidden="true">
            <path d="M10,0 C10.5,6 14,9.5 20,10 C14,10.5 10.5,14 10,20 C9.5,14 6,10.5 0,10 C6,9.5 9.5,6 10,0 Z" fill="var(--teal-text)" />
          </svg>
          Começar de novo ✨
        </button>
      )}
      <div className="feed-container" ref={feedRef}>
        <div className="feed">
          {messages.length === 0 ? (
            <div className="empty-state">
              <CloudMascot size={150} className="mascot-welcome" />
              <h1 className="empty-title">{copy.welcome.title}</h1>
              <svg className="title-squiggle" width="180" height="14" viewBox="0 0 220 16" aria-hidden="true">
                <path d="M4,8 Q30,-2 56,8 T108,8 T160,8 T212,8" stroke="var(--teal-border)" strokeWidth="5" strokeLinecap="round" fill="none" />
              </svg>
              <p className="empty-subtitle">{copy.welcome.subtitle}</p>
              <button
                type="button"
                className="get-to-know-button"
                onClick={() => handleChipClick(copy.welcome.getToKnowKickoff)}
              >
                {copy.welcome.getToKnowCta}
              </button>
            </div>
          ) : (
            messages.map(message => (
              <div key={message.id} className="bubble-group">
                <div className="question-bubble">
                  <span className="question-symbol" aria-hidden="true">
                    {copy.ui.promptSymbol}
                  </span>
                  <span className="question-text">{message.text}</span>
                </div>

                {message.response && (
                  <div className="answer-row">
                    <CloudMascot size={54} sparkle={false} className="mascot-avatar" />
                    <div className="bubble markdown-content" role="article" aria-label={copy.a11y.bubble}>
                      <ReactMarkdown>
                        {message.response}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}

          {loading && (
            <div className="loading" role="status" aria-label={copy.a11y.loading}>
              <CloudMascot size={90} mood="thinking" className="mascot-thinking" />
              <p className="loading-text">{copy.ui.thinking}</p>
              <div className="loading-dots">
                <div className="loading-dot"></div>
                <div className="loading-dot"></div>
                <div className="loading-dot"></div>
              </div>
            </div>
          )}
          
          {error && (
            <div className="error-message" role="alert">
              {error}
              <button className="retry-button" onClick={handleRetry}>
                {copy.ui.retry}
              </button>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="prompt-bar">
          {(showChips || messages.length === 0) && selectedChips.length > 0 && (
            <div className="chips" role="group" aria-label="Suggested questions">
              {selectedChips.map((chip, index) => (
                <button
                  key={index}
                  className={`chip chip--${CHIP_VARIANTS[index % CHIP_VARIANTS.length]}`}
                  onClick={() => handleChipClick(chip)}
                  aria-label={`${copy.a11y.chip}: ${chip}`}
                  tabIndex={0}
                >
                  {chip}
                </button>
              ))}
            </div>
          )}
          
          <form onSubmit={handleSubmit}>
            <div className="input-container">
              <span className="input-caret" aria-hidden="true">
                {copy.ui.promptSymbol}
              </span>
              <div className="input-field-wrap">
                <textarea
                  ref={inputRef}
                  className="input"
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value)
                    adjustTextareaHeight()
                    updateAutocomplete(e.target.value, e.target.selectionStart)
                  }}
                  onClick={(e) => {
                    if (autocomplete) updateAutocomplete(e.target.value, e.target.selectionStart)
                  }}
                  onBlur={() => setAutocomplete(null)}
                  onKeyDown={handleKeyDown}
                  placeholder={copy.ui.inputPlaceholder}
                  disabled={loading}
                  maxLength={2000}
                  rows={1}
                  aria-label={copy.a11y.input}
                  autoComplete="off"
                  autoCorrect="off"
                  spellCheck="true"
                />
                {autocomplete && (
                  <EmojiAutocomplete match={autocomplete} onSelect={selectAutocompleteEmoji} />
                )}
              </div>
              <div className="emoji-picker-anchor" ref={emojiAnchorRef}>
                <button
                  type="button"
                  className="emoji-toggle"
                  onClick={() => {
                    setAutocomplete(null)
                    setShowEmojiPicker(prev => !prev)
                  }}
                  aria-label="Abrir emojis"
                  aria-expanded={showEmojiPicker}
                >
                  😊
                </button>
                {showEmojiPicker && (
                  <EmojiPicker
                    onSelect={handleEmojiSelect}
                    onClose={() => {
                      setShowEmojiPicker(false)
                      inputRef.current?.focus()
                    }}
                  />
                )}
              </div>
              <button type="submit" className="submit" disabled={loading || !input.trim()}>
                <svg className="submit-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M2.1 12.5L19.1 5L12.1 21L9.6 14L2.1 12.5Z" fill="#fff" />
                  <path d="M9.6 14L19.1 5" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" />
                </svg>
                <span className="submit-text">{copy.ui.send}</span>
              </button>
            </div>
          </form>
      </div>
    </div>
  )
}

export default App