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
  
  // Keep focus on input field
  useEffect(() => {
    const handleFocus = () => {
      // Only refocus if nothing else is selected
      if (document.activeElement?.tagName !== 'BUTTON' && 
          document.activeElement?.tagName !== 'TEXTAREA') {
        inputRef.current?.focus()
      }
    }
    
    // Refocus on click anywhere in the app
    document.addEventListener('click', handleFocus)
    
    // Refocus when window regains focus
    window.addEventListener('focus', handleFocus)
    
    return () => {
      document.removeEventListener('click', handleFocus)
      window.removeEventListener('focus', handleFocus)
    }
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
      // Small delay to ensure DOM is updated
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }


  // Handle chip click
  const handleChipClick = (question) => {
    setInput(question)
    // Auto-submit after a brief delay for better UX
    setTimeout(() => {
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
                  <div className="bubble" role="article" aria-label={copy.a11y.bubble}>
                    <ReactMarkdown className="markdown-content">
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
                onChange={(e) => setInput(e.target.value)}
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