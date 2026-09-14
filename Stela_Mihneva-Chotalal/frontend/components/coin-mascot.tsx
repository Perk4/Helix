type CoinMascotProps = {
  className?: string
  size?: number
}

export function CoinMascot({ className, size = 48 }: CoinMascotProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="Coach Coin mascot"
    >
      <circle cx="32" cy="32" r="30" fill="#e6a700" />
      <circle cx="32" cy="30" r="26" fill="#ffd700" />
      <circle cx="32" cy="30" r="26" stroke="#e6a700" strokeWidth="2" />
      <text
        x="32"
        y="20"
        textAnchor="middle"
        fontSize="12"
        fontWeight="800"
        fill="#050f2e"
        fontFamily="var(--font-fredoka), sans-serif"
      >
        $
      </text>
      {/* eyes */}
      <circle cx="24" cy="30" r="4" fill="#050f2e" />
      <circle cx="40" cy="30" r="4" fill="#050f2e" />
      <circle cx="25.5" cy="28.5" r="1.4" fill="#fff" />
      <circle cx="41.5" cy="28.5" r="1.4" fill="#fff" />
      {/* cheeks */}
      <circle cx="18" cy="37" r="3" fill="#ffb3c1" opacity="0.7" />
      <circle cx="46" cy="37" r="3" fill="#ffb3c1" opacity="0.7" />
      {/* smile */}
      <path
        d="M24 39 Q32 46 40 39"
        stroke="#050f2e"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  )
}
