import { NextResponse } from "next/server"

// Symbols we surface in the ticker. Binance uses <BASE>USDT pairs.
const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

// api.binance.com is geo-blocked (HTTP 451) from many server regions, so we
// query hosts in order and use the first that responds. Both expose the same
// /api/v3/ticker/24hr contract.
const HOSTS = ["https://api.binance.com", "https://api.binance.us"]

type Ticker24hr = {
  symbol: string
  lastPrice: string
  priceChangePercent: string
}

export const dynamic = "force-dynamic"

export async function GET() {
  const query = `symbols=${encodeURIComponent(JSON.stringify(SYMBOLS))}`

  for (const host of HOSTS) {
    try {
      const res = await fetch(`${host}/api/v3/ticker/24hr?${query}`, {
        headers: { Accept: "application/json" },
        cache: "no-store",
      })
      if (!res.ok) continue

      const data: Ticker24hr[] = await res.json()
      const tickers = data.map(({ symbol, lastPrice, priceChangePercent }) => ({
        symbol,
        lastPrice,
        priceChangePercent,
      }))

      return NextResponse.json(
        { tickers },
        { headers: { "Cache-Control": "no-store" } },
      )
    } catch {
      // Try the next host.
    }
  }

  return NextResponse.json({ error: "Unable to reach price feed" }, { status: 502 })
}
