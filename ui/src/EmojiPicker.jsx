import React, { useState } from 'react'
import { EMOJI_CATEGORIES, EMOJIS_BY_CATEGORY, searchEmojis } from './emojiData'

// Tap-to-open emoji panel: category tabs + big touch-friendly grid, with a
// search box up top. Stays open after a pick so a slow typist can tap
// several emojis in a row, like the emoji keyboards she already knows.
function EmojiPicker({ onSelect, onClose }) {
  const [query, setQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState(EMOJI_CATEGORIES[0].id)

  const items = query ? searchEmojis(query, 60) : EMOJIS_BY_CATEGORY[activeCategory]

  // Buttons that shouldn't steal focus from the textarea when tapped.
  const keepFocus = (e) => e.preventDefault()

  return (
    <div className="emoji-picker" role="dialog" aria-label="Escolhe um emoji">
      <div className="emoji-picker-header">
        <input
          type="text"
          className="emoji-search"
          placeholder="Procurar emoji..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Procurar emoji"
        />
        <button
          type="button"
          className="emoji-picker-close"
          onMouseDown={keepFocus}
          onClick={onClose}
          aria-label="Fechar"
        >
          ×
        </button>
      </div>

      {!query && (
        <div className="emoji-tabs" role="tablist" aria-label="Categorias de emoji">
          {EMOJI_CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              type="button"
              role="tab"
              aria-selected={activeCategory === cat.id}
              className={`emoji-tab${activeCategory === cat.id ? ' emoji-tab--active' : ''}`}
              onMouseDown={keepFocus}
              onClick={() => setActiveCategory(cat.id)}
              aria-label={cat.label}
            >
              {cat.tabIcon}
            </button>
          ))}
        </div>
      )}

      <div className="emoji-grid-scroll">
        {items.length > 0 ? (
          <div className="emoji-grid">
            {items.map((emoji) => (
              <button
                key={emoji.char}
                type="button"
                className="emoji-cell"
                onMouseDown={keepFocus}
                onClick={() => onSelect(emoji.char)}
                aria-label={emoji.pt[0] || emoji.en[0]}
              >
                {emoji.char}
              </button>
            ))}
          </div>
        ) : (
          <p className="emoji-empty">Sem resultados 🔍</p>
        )}
      </div>
    </div>
  )
}

export default EmojiPicker
