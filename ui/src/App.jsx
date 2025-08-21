import React, { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { copy } from './copy'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Feature flags
const ENABLE_TTS = false // Set to true when TTS backend is ready

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
  
  const feedRef = useRef(null)
  const inputRef = useRef(null)
  const messagesEndRef = useRef(null)

  // Get random starter questions
  const getRandomChips = useCallback(() => {
    const shuffled = [...copy.starterQuestions].sort(() => 0.5 - Math.random())
    return shuffled.slice(0, 3)
  }, [])

  useEffect(() => {
    setSelectedChips(getRandomChips())
    inputRef.current?.focus()
    // Start a new session on mount
    startNewSession()
  }, [getRandomChips])
  
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

  // Scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      if (feedRef.current) {
        feedRef.current.scrollTop = feedRef.current.scrollHeight
      }
    })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

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

  // Handle input submission
  const handleSubmit = async (e) => {
    e?.preventDefault()
    
    const question = input.trim()
    if (!question || loading) return
    
    setInput('')
    setLoading(true)
    setError(null)
    setShowChips(false)
    
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
      handleSubmit()
      inputRef.current?.focus()
    }, 100)
  }

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
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
  
  // Reset conversation
  const handleReset = () => {
    setMessages([])
    setConversationHistory([])
    setInput('')
    setError(null)
    setShowChips(true)
    setSelectedChips(getRandomChips())
    startNewSession()
    inputRef.current?.focus()
  }

  return (
    <div className="app" lang="pt">
      <div className="feed-container" ref={feedRef}>
        <div className="feed">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h1 className="empty-title">{copy.welcome.title}</h1>
              <p className="empty-subtitle">{copy.welcome.subtitle}</p>
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
                  <div className="bubble markdown-content" role="article" aria-label={copy.a11y.bubble}>
                    <ReactMarkdown>
                      {message.response}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            ))
          )}
          
          {loading && (
            <div className="loading" role="status" aria-label={copy.a11y.loading}>
              <div className="loading-dot"></div>
              <div className="loading-dot"></div>
              <div className="loading-dot"></div>
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
          {messages.length > 0 && (
            <button className="reset-button" onClick={handleReset} aria-label="Nova conversa">
              Nova conversa ✨
            </button>
          )}
          {(showChips || messages.length === 0) && selectedChips.length > 0 && (
            <div className="chips" role="group" aria-label="Suggested questions">
              {selectedChips.map((chip, index) => (
                <button
                  key={index}
                  className="chip"
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
              <textarea
                ref={inputRef}
                className="input"
                value={input}
                onChange={(e) => {
                  setInput(e.target.value)
                  adjustTextareaHeight()
                }}
                onKeyDown={handleKeyDown}
                placeholder={copy.ui.inputPlaceholder}
                disabled={loading}
                maxLength={500}
                rows={1}
                aria-label={copy.a11y.input}
                autoComplete="off"
                autoCorrect="off"
                spellCheck="true"
              />
              <button type="submit" className="submit" disabled={loading || !input.trim()}>
                {copy.ui.send}
              </button>
            </div>
          </form>
      </div>
    </div>
  )
}

export default App