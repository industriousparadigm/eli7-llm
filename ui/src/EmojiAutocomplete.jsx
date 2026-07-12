import React from 'react'

// Small inline popup for the Slack-style ":gato" trigger. `match` is
// { query, results, highlighted } from App's colon-detection logic.
function EmojiAutocomplete({ match, onSelect }) {
  const { results, highlighted } = match

  return (
    <div className="emoji-autocomplete" role="listbox" aria-label="Sugestões de emoji">
      {results.map((emoji, i) => (
        <button
          key={emoji.char}
          type="button"
          role="option"
          aria-selected={i === highlighted}
          className={`emoji-autocomplete-item${i === highlighted ? ' emoji-autocomplete-item--active' : ''}`}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => onSelect(emoji)}
        >
          <span className="emoji-autocomplete-char" aria-hidden="true">{emoji.char}</span>
          <span className="emoji-autocomplete-label">{emoji.pt[0] || emoji.en[0]}</span>
        </button>
      ))}
    </div>
  )
}

export default EmojiAutocomplete
