// Blushing cloud mascot. `mood="thinking"` closes the eyes for the loading state.
function CloudMascot({ size = 120, mood = 'happy', sparkle = true, className = '' }) {
  const height = Math.round(size * 0.75)

  return (
    <svg
      className={`mascot ${className}`.trim()}
      width={size}
      height={height}
      viewBox="0 0 200 150"
      aria-hidden="true"
    >
      <ellipse cx="100" cy="132" rx="60" ry="7" fill="#4A3A5C" opacity="0.06" />
      <g fill="var(--mascot-shadow)">
        <rect x="24" y="68" width="152" height="60" rx="30" />
        <circle cx="54" cy="72" r="38" />
        <circle cx="100" cy="52" r="46" />
        <circle cx="150" cy="74" r="36" />
      </g>
      <g fill="var(--mascot-body)">
        <rect x="28" y="72" width="144" height="52" rx="26" />
        <circle cx="54" cy="72" r="34" />
        <circle cx="100" cy="52" r="42" />
        <circle cx="150" cy="74" r="32" />
      </g>
      {sparkle && (
        <path
          className="mascot-sparkle"
          transform="translate(126,14)"
          d="M0,-11 C0.5,-2 4,1.5 12,2 C4,2.5 0.5,6 0,15 C-0.5,6 -4,2.5 -12,2 C-4,1.5 -0.5,-2 0,-11 Z"
          fill="var(--mascot-sparkle)"
        />
      )}
      {mood === 'thinking' ? (
        <>
          <path d="M72,60 Q80,52 88,60" fill="none" stroke="var(--mascot-face)" strokeWidth="4" strokeLinecap="round" />
          <path d="M112,60 Q120,52 128,60" fill="none" stroke="var(--mascot-face)" strokeWidth="4" strokeLinecap="round" />
          <ellipse cx="65" cy="76" rx="9" ry="5" fill="var(--mascot-blush)" opacity="0.75" />
          <ellipse cx="135" cy="76" rx="9" ry="5" fill="var(--mascot-blush)" opacity="0.75" />
          <path d="M90,82 Q100,90 110,82" fill="none" stroke="var(--mascot-face)" strokeWidth="4" strokeLinecap="round" />
        </>
      ) : (
        <>
          <circle cx="80" cy="60" r="7" fill="var(--mascot-face)" />
          <circle cx="82.5" cy="57" r="2.1" fill="#fff" />
          <circle cx="120" cy="60" r="7" fill="var(--mascot-face)" />
          <circle cx="122.5" cy="57" r="2.1" fill="#fff" />
          <ellipse cx="65" cy="74" rx="9" ry="5" fill="var(--mascot-blush)" opacity="0.75" />
          <ellipse cx="135" cy="74" rx="9" ry="5" fill="var(--mascot-blush)" opacity="0.75" />
          <path d="M88,78 Q100,90 112,78" fill="none" stroke="var(--mascot-face)" strokeWidth="4" strokeLinecap="round" />
        </>
      )}
    </svg>
  )
}

export default CloudMascot
