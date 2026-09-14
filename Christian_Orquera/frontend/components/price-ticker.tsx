"use client"

import useSWR from "swr"
import { ArrowDownRight, ArrowUpRight } from "lucide-react"

const COINS = [
  { symbol: "BTCUSDT", label: "BTC" },
  { symbol: "ETHUSDT", label: "ETH" },
  { symbol: "SOLUSDT", label: "SOL" },
] as const

type Ticker24hr = {
  symbol: string
  lastPrice: string
  priceChangePercent: string
}

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

async function fetchTickers(): Promise<Record<string, Ticker24hr>> {
  const res = await fetch("/api/ticker")
  if (!res.ok) throw new Error(`Ticker request failed with status ${res.status}`)
  const data: { tickers: Ticker24hr[] } = await res.json()
  return Object.fromEntries(data.tickers.map((t) => [t.symbol, t]))
}

export function PriceTicker() {
  const { data, error, isLoading } = useSWR("binance-24hr", fetchTickers, {
    refreshInterval: 10_000,
    revalidateOnFocus: false,
    keepPreviousData: true,
  })

  return (
    <div
      className="flex items-stretch gap-2 overflow-x-auto border-b border-primary/15 bg-card/60 px-4 py-2.5 sm:gap-3 sm:px-6"
      role="marquee"
      aria-label="Live cryptocurrency prices"
    >
      {COINS.map((coin) => {
        const ticker = data?.[coin.symbol]
        const changePercent = ticker ? Number.parseFloat(ticker.priceChangePercent) : null
        const price = ticker ? Number.parseFloat(ticker.lastPrice) : null
        const isUp = changePercent !== null && changePercent >= 0

        return (
          <div
            key={coin.symbol}
            className="flex min-w-[7.5rem] flex-1 items-center justify-between gap-3 rounded-lg bg-background/40 px-3 py-2 ring-1 ring-primary/10"
          >
            <div className="flex flex-col">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                {coin.label}
              </span>
              {price !== null ? (
                <span className="font-mono text-sm font-semibold text-foreground tabular-nums">
                  {usd.format(price)}
                </span>
              ) : error && !isLoading ? (
                <span className="text-sm text-muted-foreground">—</span>
              ) : (
                <span className="h-4 w-16 animate-pulse rounded bg-muted-foreground/20" aria-hidden="true" />
              )}
            </div>
            {changePercent !== null ? (
              <span
                className={`inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 font-mono text-xs font-medium tabular-nums ${
                  isUp
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-red-500/10 text-red-400"
                }`}
              >
                {isUp ? (
                  <ArrowUpRight className="h-3 w-3" />
                ) : (
                  <ArrowDownRight className="h-3 w-3" />
                )}
                {isUp ? "+" : ""}
                {changePercent.toFixed(2)}%
              </span>
            ) : (
              <span className="h-5 w-14 animate-pulse rounded bg-muted-foreground/20" aria-hidden="true" />
            )}
          </div>
        )
      })}
    </div>
  )
}
